import React, { useState } from "react";

export default function LookupSplitScreen() {
  const [query, setQuery] = useState("");
  const [data, setData] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    const res = await fetch(`/lookup?q=${encodeURIComponent(query)}`);
    const json = await res.json();
    setData(json);
  };

  return (
    <div className="p-6">
      <form onSubmit={handleSearch} className="mb-4 flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type a conditionxx (e.g. obesity)"
          className="border rounded p-2 flex-1"
        />
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded"
        >
          Search
        </button>
      </form>

      {data && (
        <div className="grid grid-cols-2 gap-6">
          {/* Patient View */}
          <div className="border rounded p-4 bg-gray-50">
            <h2 className="font-bold text-lg mb-2">Patient View</h2>
            {data.patientView.length > 0 ? (
              <ul className="list-disc pl-5">
                {data.patientView.map((term, i) => (
                  <li key={i} className="text-blue-800 font-medium">
                    {term}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">No patient-friendly matches</p>
            )}
          </div>

          {/* Practitioner View */}
          <div className="border rounded p-4 bg-white">
            <h2 className="font-bold text-lg mb-2">Practitioner View</h2>
            {data.practitionerView.length > 0 ? (
              <ul className="space-y-2">
                {data.practitionerView.map((code, i) => (
                  <li key={i} className="text-gray-700">
                    <div className="font-medium">{code.display}</div>
                    <div className="text-xs text-gray-500">
                      {code.system} | {code.code}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">No practitioner codes</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
