import os
import ffmpeg
from PIL import Image
from django.core.files.base import ContentFile
from django.conf import settings

class MediaScrubberService:
    @staticmethod
    def process_evidence(evidence_instance):
        """Strips EXIF data from images and removes audio tracks from videos."""
        raw_path = evidence_instance.original_file.path
        filename = os.path.basename(raw_path)
        clean_dir = os.path.join(settings.MEDIA_ROOT, "evidence", "clean")
        os.makedirs(clean_dir, exist_ok=True)
        
        clean_path = os.path.join(clean_dir, f"clean_{filename}")

        try:
            if evidence_instance.file_type == "IMAGE":
                # 1. Open photo, strip EXIF by copying only pixel data to a clean image canvas
                with Image.open(raw_path) as img:
                    data = list(img.getdata())
                    clean_img = Image.new(img.mode, img.size)
                    clean_img.putdata(data)
                    clean_img.save(clean_path, format=img.format or "JPEG", quality=85)

            elif evidence_instance.file_type == "VIDEO":
                # 2. Use FFmpeg to copy video stream while dropping audio stream (-an flag)
                (
                    ffmpeg
                    .input(raw_path)
                    .output(clean_path, vcodec='copy', an=None) # 'an=None' removes audio
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )

            # Save the scrubbed file path back to the database model
            with open(clean_path, 'rb') as f:
                evidence_instance.scrubbed_file.save(f"clean_{filename}", ContentFile(f.read()), save=False)
            
            evidence_instance.is_processed = True
            evidence_instance.save()
            
            # Optional: Delete raw file from server to conserve disk space and guarantee privacy
            if os.path.exists(raw_path):
                os.remove(raw_path)

        except Exception as e:
            print(f"Media scrubbing failed for Evidence #{evidence_instance.id}: {str(e)}")
            raise e