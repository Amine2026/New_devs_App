import React, { useEffect, useState } from "react";
import { RevenueSummary } from "./RevenueSummary";
import { SecureAPI } from "../lib/secureApi";
import { useAuth } from "../contexts/AuthContext.new";

interface PropertyOption {
  id: string;
  name: string;
  timezone?: string;
}

const TENANT_FALLBACK_PROPERTIES: Record<string, PropertyOption[]> = {
  "tenant-a": [
    { id: "prop-001", name: "Beach House Alpha", timezone: "Europe/Paris" },
    { id: "prop-002", name: "City Apartment Downtown", timezone: "Europe/Paris" },
    { id: "prop-003", name: "Country Villa Estate", timezone: "Europe/Paris" },
  ],
  "tenant-b": [
    { id: "prop-001", name: "Mountain Lodge Beta", timezone: "America/New_York" },
    { id: "prop-004", name: "Lakeside Cottage", timezone: "America/New_York" },
    { id: "prop-005", name: "Urban Loft Modern", timezone: "America/New_York" },
  ],
};

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const tenantId =
    user?.tenant_id ||
    user?.app_metadata?.tenant_id ||
    user?.user_metadata?.tenant_id ||
    "tenant-a";

  const [properties, setProperties] = useState<PropertyOption[]>(
    TENANT_FALLBACK_PROPERTIES[tenantId] || TENANT_FALLBACK_PROPERTIES["tenant-a"]
  );
  const [selectedProperty, setSelectedProperty] = useState("prop-001");

  useEffect(() => {
    let mounted = true;
    const fallbackList =
      TENANT_FALLBACK_PROPERTIES[tenantId] || TENANT_FALLBACK_PROPERTIES["tenant-a"];
    setProperties(fallbackList);

    SecureAPI.getDashboardProperties()
      .then((list) => {
        if (!mounted || !Array.isArray(list) || list.length === 0) return;
        setProperties(list);
        if (!list.some((p) => p.id === selectedProperty)) {
          setSelectedProperty(list[0].id);
        }
      })
      .catch(() => {
        if (!mounted) return;
        if (!fallbackList.some((p) => p.id === selectedProperty)) {
          setSelectedProperty(fallbackList[0].id);
        }
      });

    return () => {
      mounted = false;
    };
  }, [tenantId]);

  return (
    <div className="p-4 lg:p-6 min-h-full">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-900">Property Management Dashboard</h1>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 lg:p-6">
          <div className="mb-6">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
              <div>
                <h2 className="text-lg lg:text-xl font-medium text-gray-900 mb-2">Revenue Overview</h2>
                <p className="text-sm lg:text-base text-gray-600">
                  Monthly performance insights for your properties
                </p>
              </div>
              
              {/* Property Selector */}
              <div className="flex flex-col sm:items-end">
                <label className="text-xs font-medium text-gray-700 mb-1">Select Property</label>
                <select
                  value={selectedProperty}
                  onChange={(e) => setSelectedProperty(e.target.value)}
                  className="block w-full sm:w-auto min-w-[200px] px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                >
                  {properties.map((property) => (
                    <option key={property.id} value={property.id}>
                      {property.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <RevenueSummary propertyId={selectedProperty} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
