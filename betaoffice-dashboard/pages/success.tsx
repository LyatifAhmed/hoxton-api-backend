import { useEffect } from 'react';
import { useRouter } from 'next/router';

export default function SuccessPage() {
  const router = useRouter();

  useEffect(() => {
    // Mark payment as complete in localStorage
    localStorage.setItem('paymentCompleted', 'true');
    // Redirect to KYC form
    router.push('/kyc');
  }, []);

  return (
    <div className="p-6 text-center">
      <h1 className="text-3xl font-bold">Redirecting to KYC Form...</h1>
    </div>
  );
}

  