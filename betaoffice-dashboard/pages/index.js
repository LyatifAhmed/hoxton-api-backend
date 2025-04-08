"use client";
import { loadStripe } from "@stripe/stripe-js";
import { useCallback } from "react";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY,);

export default function HomePage() {
  const handleCheckout = useCallback(async (priceId, string) => {
    const stripe = await stripePromise;

    const response = await fetch("/api/checkout-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ priceId }),
    });

    const data = await response.json();

    if (data.sessionId && stripe) {
      await stripe.redirectToCheckout({ sessionId: data.sessionId });
    } else {
      alert("Unable to start checkout");
    }
  }, []);

  return (
    <div>
      {/* Hero Section */}
      <div
        className="min-h-screen bg-cover bg-center flex items-center justify-center text-white"
        style={{ backgroundImage: "url('/office-bg.png')" }}
      >
        <div className="bg-black bg-opacity-60 p-10 rounded shadow-lg text-center max-w-xl">
          <h1 className="text-4xl font-bold mb-4">Welcome to BetaOffice</h1>
          <p className="text-lg mb-6">
            Get your professional office address in London. We scan and forward your mail. It&apos;s fast, secure, and smart.
          </p>
          <button
            onClick={() => {
              document.getElementById("pricing")?.scrollIntoView({ behavior: "smooth" });
            }}
            className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded"
          >
            Get Started
          </button>
        </div>
      </div>

      {/* Features Section */}
      <section id="features" className="py-20 bg-white text-gray-900">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center mb-12">Why Choose BetaOffice?</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            <div className="bg-gray-100 p-6 rounded-lg shadow hover:shadow-lg transition-all">
              <h3 className="text-xl font-semibold mb-2">📍 Prime London Address</h3>
              <p>Use a real business address in Central London to boost your company’s credibility and image.</p>
            </div>
            <div className="bg-gray-100 p-6 rounded-lg shadow hover:shadow-lg transition-all">
              <h3 className="text-xl font-semibold mb-2">📬 Scanned Mail Access</h3>
              <p>We scan your incoming letters so you can read them anytime, anywhere — fully automated.</p>
            </div>
            <div className="bg-gray-100 p-6 rounded-lg shadow hover:shadow-lg transition-all">
              <h3 className="text-xl font-semibold mb-2">🚚 Optional Mail Forwarding</h3>
              <p>Need physical copies? We forward mail to your chosen address on request.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-gray-50 text-gray-900">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center mb-12">Simple Pricing (All plans + VAT)</h2>
          <div className="flex flex-col md:flex-row gap-10 justify-center">

            {/* Monthly Plan */}
            <div className="bg-white border rounded-lg p-6 shadow-md max-w-sm">
              <h3 className="text-xl font-semibold mb-2">Monthly Plan</h3>
              <p className="text-3xl font-bold">£20<span className="text-base font-normal">/month</span></p>
              <p className="text-sm text-gray-500 mb-4">+ VAT (£24 total)</p>
              <ul className="text-gray-700 space-y-2 mb-6">
                <li>✓ London business address</li>
                <li>✓ Scanned letters to your dashboard</li>
                <li>✓ Email notifications</li>
                <li>✓ Cancel anytime</li>
              </ul>
              <button
                onClick={() => handleCheckout(process.env.NEXT_PUBLIC_STRIPE_MONTHLY_PRICE_ID,)}
                className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded w-full"
              >
                Choose Monthly
              </button>
            </div>

            {/* Annual Plan */}
            <div className="bg-white border-2 border-blue-500 rounded-lg p-6 shadow-md max-w-sm relative">
              <span className="absolute -top-3 -right-3 bg-blue-500 text-white text-xs font-bold px-2 py-1 rounded-full">
                Best Value
              </span>
              <h3 className="text-xl font-semibold mb-2">Annual Plan</h3>
              <p className="text-3xl font-bold">£200<span className="text-base font-normal">/year</span></p>
              <p className="text-sm text-gray-500 mb-4">+ VAT (£240 total)</p>
              <ul className="text-gray-700 space-y-2 mb-6">
                <li>✓ All monthly features</li>
                <li>✓ Save £48/year</li>
                <li>✓ Priority support</li>
                <li>✓ Mail forwarding available (pay per item)</li>
              </ul>
              <button
                onClick={() => handleCheckout(process.env.NEXT_PUBLIC_STRIPE_ANNUAL_PRICE_ID,)}
                className="bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-4 rounded w-full"
              >
                Choose Annual
              </button>
            </div>

          </div>
        </div>
      </section>
    </div>
  );
}
