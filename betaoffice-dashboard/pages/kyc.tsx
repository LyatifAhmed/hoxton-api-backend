import React, { useState, useEffect } from "react";
import PhoneInput from "react-phone-input-2";
import "react-phone-input-2/lib/style.css";
import axios from "axios";
import Select from "react-select";

export default function KYCForm() {
  const [owners, setOwners] = useState([{ id: Date.now() }]);
  const [manualAddress, setManualAddress] = useState(false);
  const [manualCompany, setManualCompany] = useState(false);
  const [postcode, setPostcode] = useState("");
  const [addressOptions, setAddressOptions] = useState([]);
  const [companyOptions, setCompanyOptions] = useState([]);
  const [selectedAddress, setSelectedAddress] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState(null);

  const addOwner = () => setOwners([...owners, { id: Date.now() }]);
  const removeOwner = (id: number) => setOwners(owners.filter(o => o.id !== id));

  const fetchAddresses = async () => {
    if (!postcode) return;
    try {
      const res = await axios.get(`https://hoxton-api-backend.onrender.com/api/address-lookup?postcode=${postcode}`)

      setAddressOptions(res.data.addresses.map((a: string) => ({ label: a, value: a })));
    } catch (err) {
      console.error("Address lookup failed", err);
    }
  };

  const fetchCompanies = async (search: string) => {
    try {
      const res = await axios.get(`/api/companies?query=${search}`);
      setCompanyOptions(res.data.map((c: any) => ({ label: c.title, value: c.title })));
    } catch (err) {
      console.error("Company search failed", err);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <h1 className="text-3xl font-bold mb-8">KYC Form</h1>
      <form className="space-y-10">
        {/* Contact Information */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Contact Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input type="text" placeholder="First Name" className="border p-2 rounded w-full" required />
            <input type="text" placeholder="Last Name" className="border p-2 rounded w-full" required />
            <input type="email" placeholder="Email Address" className="border p-2 rounded w-full" required />
            <PhoneInput
  country={"gb"}
  inputStyle={{
    width: "100%",
    height: "42px",
    paddingLeft: "58px",
    fontSize: "16px",
    borderRadius: "0.375rem",
    border: "1px solid #d1d5db",
  }}
  buttonStyle={{
    height: "42px",
    width: "56px",
    borderTopLeftRadius: "0.375rem",
    borderBottomLeftRadius: "0.375rem",
    borderRight: "1px solid #d1d5db",
    backgroundColor: "white",
  }}
  containerStyle={{ width: "100%" }}
/>

          </div>
        </section>

        {/* Address Section */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Address</h2>
          {!manualAddress ? (
            <>
              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  value={postcode}
                  onChange={e => setPostcode(e.target.value)}
                  placeholder="Postcode"
                  className="border p-2 rounded w-full"
                />
                <button
                  type="button"
                  onClick={fetchAddresses}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-4 rounded"
                >
                  Lookup
                </button>
              </div>
              <Select
                options={addressOptions}
                placeholder="Select an address"
                value={selectedAddress}
                onChange={setSelectedAddress}
              />
              <button
                type="button"
                onClick={() => setManualAddress(true)}
                className="text-blue-600 underline mt-3 text-sm"
              >
                Enter address manually
              </button>
            </>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input type="text" placeholder="Address Line 1" className="border p-2 rounded w-full" />
                <input type="text" placeholder="Address Line 2" className="border p-2 rounded w-full" />
                <input type="text" placeholder="City" className="border p-2 rounded w-full" />
                <input type="text" placeholder="Postcode" className="border p-2 rounded w-full" />
              </div>
              <button
                type="button"
                onClick={() => setManualAddress(false)}
                className="text-blue-600 underline mt-3 text-sm"
              >
                Use postcode lookup instead
              </button>
            </>
          )}
        </section>

        {/* Company Info */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Company Information</h2>
          {!manualCompany ? (
            <>
              <Select
                placeholder="Search company name"
                onInputChange={fetchCompanies}
                options={companyOptions}
                onChange={setSelectedCompany}
              />
              <button
                type="button"
                onClick={() => setManualCompany(true)}
                className="text-blue-600 underline mt-3 text-sm"
              >
                Enter company manually
              </button>
            </>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input type="text" placeholder="Company Name" className="border p-2 rounded w-full" />
                <input type="text" placeholder="Trading Name" className="border p-2 rounded w-full" />
                <input type="text" placeholder="Company Number" className="border p-2 rounded w-full" />
                <select className="border p-2 rounded w-full">
                  <option value="">Organisation Type</option>
                  <option value="limited">Limited Company</option>
                  <option value="unincorporated">Unincorporated / Not registered yet</option>
                </select>
              </div>
              <button
                type="button"
                onClick={() => setManualCompany(false)}
                className="text-blue-600 underline mt-3 text-sm"
              >
                Use search instead
              </button>
            </>
          )}
        </section>

        {/* Business Owners */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Business Owners / UBOs</h2>
          {owners.map(owner => (
            <div key={owner.id} className="mb-6 border p-4 rounded shadow relative">
              {owners.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeOwner(owner.id)}
                  className="absolute top-2 right-2 text-red-500 hover:text-red-700"
                >
                  Remove Owner
                </button>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input type="text" placeholder="First Name" className="border p-2 rounded w-full" />
                <input type="text" placeholder="Last Name" className="border p-2 rounded w-full" />
                <label className="md:col-span-2 text-sm text-gray-700">Date of Birth</label>
                <input type="date" className="border p-2 rounded w-full md:col-span-2" />
                <PhoneInput
  country={"gb"}
  inputStyle={{
    width: "100%",
    height: "42px",
    paddingLeft: "58px",
    fontSize: "16px",
    borderRadius: "0.375rem",
    border: "1px solid #d1d5db",
  }}
  buttonStyle={{
    height: "42px",
    width: "56px",
    borderTopLeftRadius: "0.375rem",
    borderBottomLeftRadius: "0.375rem",
    borderRight: "1px solid #d1d5db",
    backgroundColor: "white",
  }}
  containerStyle={{ width: "100%" }}
/>

                <div className="md:col-span-1">
                  <label className="text-sm text-gray-700 mb-1 block">Proof of ID</label>
                  <input type="file" accept=".pdf,.jpg,.png" className="border p-2 rounded w-full" />
                </div>
                <div className="md:col-span-1">
                  <label className="text-sm text-gray-700 mb-1 block">Proof of Address</label>
                  <input type="file" accept=".pdf,.jpg,.png" className="border p-2 rounded w-full" />
                </div>
              </div>
            </div>
          ))}
          <button
            type="button"
            onClick={addOwner}
            className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded"
          >
            Add Another Owner
          </button>
        </section>

        {/* Submit */}
        <div className="text-center">
          <button
            type="submit"
            className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-6 rounded"
          >
            Submit
          </button>
        </div>
      </form>
    </div>
  );
}




