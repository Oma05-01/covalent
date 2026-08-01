import React, { useState, useEffect } from 'react';

const CountdownTimer = ({ targetDate, onExpire }) => {
  // Helper to calculate the exact difference down to the second
  const calculateTimeLeft = () => {
    const difference = new Date(targetDate) - new Date();
    
    if (difference <= 0) return null;

    return {
      days: Math.floor(difference / (1000 * 60 * 60 * 24)),
      hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
      minutes: Math.floor((difference / 1000 / 60) % 60),
      seconds: Math.floor((difference / 1000) % 60)
    };
  };

  const [timeLeft, setTimeLeft] = useState(calculateTimeLeft());

  useEffect(() => {
    // Start ticking every 1,000 milliseconds
    const timer = setInterval(() => {
      const remaining = calculateTimeLeft();
      setTimeLeft(remaining);

      // Stop the timer when it hits zero
      if (!remaining) {
        clearInterval(timer);
        if (onExpire) onExpire();
      }
    }, 1000);

    // Cleanup function prevents memory leaks when navigating away from the page
    return () => clearInterval(timer);
  }, [targetDate, onExpire]);

  // What to show when the timer hits zero
  if (!timeLeft) {
    return (
      <div className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-md font-semibold">
        Inspection window expired.
      </div>
    );
  }

  // Formatting single digits to always show two digits (e.g., "05" instead of "5")
  const format = (num) => String(num).padStart(2, '0');

  return (
    <div className="flex items-center space-x-2 text-xl font-mono font-bold text-gray-800">
      {timeLeft.days > 0 && (
        <span className="text-gray-500 text-sm mr-2">{timeLeft.days}d</span>
      )}
      <div className="bg-gray-100 px-2 py-1 rounded shadow-inner">{format(timeLeft.hours)}</div>
      <span className="text-gray-400 animate-pulse">:</span>
      <div className="bg-gray-100 px-2 py-1 rounded shadow-inner">{format(timeLeft.minutes)}</div>
      <span className="text-gray-400 animate-pulse">:</span>
      <div className="bg-blue-50 text-blue-600 px-2 py-1 rounded shadow-inner">{format(timeLeft.seconds)}</div>
    </div>
  );
};

export default CountdownTimer;