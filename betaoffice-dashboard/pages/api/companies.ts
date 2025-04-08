// pages/api/companies.ts
import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { query } = req.query;

  if (!query || typeof query !== "string") {
    return res.status(400).json({ error: "Missing or invalid query parameter" });
  }

  const API_KEY = process.env.NEXT_PUBLIC_COMPANY_HOUSE_API_KEY;
  const url = `https://api.company-information.service.gov.uk/search/companies?q=${encodeURIComponent(query)}`;

  try {
    const response = await fetch(url, {
      headers: {
        Authorization: `Basic ${btoa(`${API_KEY}:`)}`,
      },
    });

    if (!response.ok) {
      return res.status(response.status).json({ error: "Failed to fetch company data" });
    }

    const data = await response.json();

    const companies = data.items.map((company: any) => ({
      name: company.title,
      companyNumber: company.company_number,
      address: company.address_snippet,
      status: company.company_status,
    }));

    res.status(200).json({ companies });
  } catch (err) {
    console.error("Company search error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
}
