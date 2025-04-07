import Head from 'next/head';

export default function Home() {
  return (
    <>
      <Head>
        <title>BetaOffice – Professional Business Address & Virtual Mail</title>
      </Head>
      <main className="min-h-screen bg-white text-black flex flex-col items-center justify-center p-6">
        <h1 className="text-4xl font-bold mb-4 text-center">Professional Business Address & Virtual Mail Service</h1>
        <p className="text-lg mb-6 text-gray-600 max-w-xl text-center">
          Use our prestigious Central London address for your company — perfect for registration, credibility, and receiving business mail.
          We scan all your letters so you can view them instantly online.
        </p>
        <div className="flex gap-4">
          <button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded">
            Get Started
          </button>
          <button className="bg-gray-200 hover:bg-gray-300 text-black font-semibold py-2 px-4 rounded">
            Learn More
          </button>
        </div>
      </main>
    </>
  );
}
