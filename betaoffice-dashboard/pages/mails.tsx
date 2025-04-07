import { useEffect, useState } from 'react';
import axios from 'axios';

export default function MailPage() {
  const [mails, setMails] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMails = async () => {
      try {
        const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/mails`);
        setMails(res.data);
      } catch (error) {
        console.error("Failed to fetch mails:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchMails(); // ✅ run inside useEffect
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Scanned Mails</h1>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <ul className="space-y-4">
          {mails.map((mail) => (
            <li key={mail.id} className="p-4 border rounded shadow">
              <p><strong>Sender:</strong> {mail.sender_name}</p>
              <p><strong>Title:</strong> {mail.document_title}</p>
              <p><strong>Summary:</strong> {mail.summary}</p>
              <p><strong>Received:</strong> {new Date(mail.received_at).toLocaleString()}</p>
              <a
                href={mail.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline"
              >
                View PDF
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
