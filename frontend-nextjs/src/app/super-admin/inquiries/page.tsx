'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useSuperAdminAuth } from '@/contexts/SuperAdminAuthContext';
import { apiConfig } from '@/lib/api-config';
import { superAdminFetch } from '@/lib/super-admin-fetch';
import {
  InboxIcon,
  ArrowLeftIcon,
  EnvelopeIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

interface Inquiry {
  id: number;
  name: string;
  email: string;
  phone?: string | null;
  company?: string | null;
  company_size?: string | null;
  infrastructure_type?: string | null;
  itsm_tools?: string | null;
  monitoring_tools?: string | null;
  top_incident_pain?: string | null;
  node_count_estimate?: string | null;
  status: string;
  created_at: string;
}

const STATUS_OPTIONS = ['new', 'contacted', 'approved', 'converted', 'closed'] as const;

export default function InquiriesPage() {
  const router = useRouter();
  const { token } = useSuperAdminAuth();
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inquiryDetail, setInquiryDetail] = useState<Inquiry | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const fetchInquiries = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const response = await superAdminFetch(
        apiConfig.endpoints.superAdmin.inquiries(),
        token
      );
      if (!response.ok) {
        throw new Error('Failed to fetch inquiries');
      }
      const data = await response.json();
      setInquiries(data.inquiries || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch inquiries');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      fetchInquiries();
    }
  }, [token, fetchInquiries]);

  const handleStatusChange = async (inquiryId: number, newStatus: string) => {
    if (!token) return;
    setUpdatingId(inquiryId);
    setError(null);
    try {
      const response = await superAdminFetch(
        apiConfig.endpoints.superAdmin.updateInquiryStatus(inquiryId),
        token,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: newStatus }),
        }
      );
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to update status');
      }
      await fetchInquiries();
      setInquiryDetail((d) =>
        d?.id === inquiryId ? { ...d, status: newStatus } : d
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/super-admin')}
              className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900"
            >
              <ArrowLeftIcon className="h-5 w-5" />
              Back
            </button>
            <div className="flex items-center gap-3">
              <InboxIcon className="h-8 w-8 text-primary-600" />
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">
                  Trial Intake Inquiries
                </h1>
                <p className="text-sm text-neutral-600">
                  Submissions from the marketing site book-pilot form
                </p>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
            <button
              onClick={() => setError(null)}
              className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
            >
              Dismiss
            </button>
          </div>
        )}

        <div className="bg-white rounded-xl border border-neutral-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto" />
              <p className="mt-4 text-neutral-600">Loading inquiries...</p>
            </div>
          ) : inquiries.length === 0 ? (
            <div className="p-12 text-center text-neutral-500">
              <InboxIcon className="h-16 w-16 mx-auto text-neutral-300 mb-4" />
              <p>No inquiries yet.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-neutral-50 border-b border-neutral-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                      Name / Company
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                      Email
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                      Company Size
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                      Top Pain
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200">
                  {inquiries.map((inquiry) => (
                    <tr
                      key={inquiry.id}
                      className="hover:bg-neutral-50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-neutral-900">
                          {inquiry.name}
                        </div>
                        <div className="text-sm text-neutral-500">
                          {inquiry.company || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <a
                          href={`mailto:${inquiry.email}`}
                          className="text-primary-600 hover:underline flex items-center gap-1"
                        >
                          <EnvelopeIcon className="h-4 w-4" />
                          {inquiry.email}
                        </a>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-600">
                        {inquiry.company_size || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-600">
                        {inquiry.top_incident_pain || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <select
                          value={inquiry.status}
                          onChange={(e) =>
                            handleStatusChange(inquiry.id, e.target.value)
                          }
                          disabled={updatingId === inquiry.id}
                          className="text-sm rounded border border-neutral-300 px-2 py-1 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
                        >
                          {STATUS_OPTIONS.map((s) => (
                            <option key={s} value={s}>
                              {s.charAt(0).toUpperCase() + s.slice(1)}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-500">
                        {inquiry.created_at
                          ? new Date(inquiry.created_at).toLocaleDateString()
                          : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <button
                          onClick={() => setInquiryDetail(inquiry)}
                          className="text-sm text-primary-600 hover:underline"
                        >
                          View details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {inquiryDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-neutral-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-neutral-900">
                Inquiry details
              </h3>
              <button
                onClick={() => setInquiryDetail(null)}
                className="p-2 text-neutral-500 hover:text-neutral-700 rounded-lg hover:bg-neutral-100"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <DetailRow label="Name" value={inquiryDetail.name} />
              <DetailRow
                label="Email"
                value={
                  <a
                    href={`mailto:${inquiryDetail.email}`}
                    className="text-primary-600 hover:underline"
                  >
                    {inquiryDetail.email}
                  </a>
                }
              />
              {inquiryDetail.phone && (
                <DetailRow
                  label="Phone"
                  value={
                    <a
                      href={`tel:${inquiryDetail.phone}`}
                      className="text-neutral-900"
                    >
                      {inquiryDetail.phone}
                    </a>
                  }
                />
              )}
              {inquiryDetail.company && (
                <DetailRow label="Company" value={inquiryDetail.company} />
              )}
              {inquiryDetail.company_size && (
                <DetailRow
                  label="Company size"
                  value={inquiryDetail.company_size}
                />
              )}
              {inquiryDetail.infrastructure_type && (
                <DetailRow
                  label="Infrastructure type"
                  value={inquiryDetail.infrastructure_type}
                />
              )}
              {inquiryDetail.itsm_tools && (
                <DetailRow label="ITSM tools" value={inquiryDetail.itsm_tools} />
              )}
              {inquiryDetail.monitoring_tools && (
                <DetailRow
                  label="Monitoring tools"
                  value={inquiryDetail.monitoring_tools}
                />
              )}
              {inquiryDetail.top_incident_pain && (
                <DetailRow
                  label="Top incident pain"
                  value={inquiryDetail.top_incident_pain}
                />
              )}
              {inquiryDetail.node_count_estimate && (
                <DetailRow
                  label="Node count estimate"
                  value={inquiryDetail.node_count_estimate}
                />
              )}
              <DetailRow label="Status" value={inquiryDetail.status} />
              <DetailRow
                label="Submitted"
                value={
                  inquiryDetail.created_at
                    ? new Date(inquiryDetail.created_at).toLocaleString()
                    : '-'
                }
              />
              <div>
                <span className="text-xs font-medium text-neutral-500 uppercase">
                  Update status
                </span>
                <select
                  value={inquiryDetail.status}
                  onChange={(e) =>
                    handleStatusChange(inquiryDetail.id, e.target.value)
                  }
                  disabled={updatingId === inquiryDetail.id}
                  className="mt-1 block w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
                >
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div>
      <span className="text-xs font-medium text-neutral-500 uppercase">
        {label}
      </span>
      <div className="mt-1 text-neutral-900">{value}</div>
    </div>
  );
}
