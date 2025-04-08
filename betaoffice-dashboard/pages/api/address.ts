// pages/api/address.ts
import type { NextApiRequest, NextApiResponse } from 'next';
const apiKey = process.env.NEXT_PUBLIC_GETADDRESS_API_KEY;

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { postcode } = req.query;
  if (!postcode) return res.status(400).json({ error: "Postcode is required" });

  try {
    const response = await fetch(`https://api.getaddress.io/find/${postcode}?api-key=${apiKey}`);
    const data = await response.json();
    res.status(200).json(data);
  } catch (err) {
    res.status(500).json({ error: "Failed to fetch address" });
  }
}
