import json
from google import genai
from google.genai import types
from rest_framework.exceptions import ValidationError

class AIContractService:
    
    def __init__(self):
        from django.conf import settings
        if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
            raise ValidationError("Gemini API key is not configured.")
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def parse_contract_prompt(self, user_prompt):
        """Uses Gemini to convert messy user text into a structured JSON contract."""
        
        # Define the exact schema we want Gemini to return
        contract_schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "item_title": types.Schema(type=types.Type.STRING, description="Short, clean title of the item"),
                "item_description": types.Schema(type=types.Type.STRING, description="Detailed specs: size, color, condition, model"),
                "item_amount": types.Schema(type=types.Type.NUMBER, description="Cost of the item in Naira (numbers only)"),
                "delivery_fee": types.Schema(type=types.Type.NUMBER, description="Cost of dispatch rider/delivery in Naira (default 0 if unspecified)"),
                "delivery_days": types.Schema(type=types.Type.INTEGER, description="Estimated days until delivery (default 2 if unspecified)"),
                "plain_language_summary": types.Schema(type=types.Type.STRING, description="A 2-sentence bulleted summary explaining the deal terms simply to protect both parties.")
            },
            required=["item_title", "item_description", "item_amount", "delivery_fee", "delivery_days", "plain_language_summary"]
        )

        system_instruction = (
            "You are an AI escrow contract mediator for Covalent in Nigeria. "
            "Analyze the user's negotiation text and extract the exact commercial terms into JSON. "
            "If currency is mentioned in 'k' (e.g., 50k), convert it to thousands (50000)."
        )

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=contract_schema,
                    temperature=0.1, # Low temperature for factual extraction
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            raise ValidationError(f"AI contract generation failed: {str(e)}")