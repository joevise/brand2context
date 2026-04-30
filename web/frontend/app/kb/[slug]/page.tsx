"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Copy, Check, Globe, Package, Shield, MessageCircle, ChevronDown, Zap, Calendar } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="p-1.5 rounded hover:bg-[var(--muted)] transition"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

function Accordion({ title, icon: Icon, children, defaultOpen = false }: any) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-[var(--border)] rounded-xl overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full px-5 py-4 flex items-center justify-between bg-[var(--card)] hover:bg-[var(--muted)] transition">
        <span className="flex items-center gap-2 font-semibold"><Icon className="w-5 h-5 text-primary-600" />{title}</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && <div className="px-5 py-4 bg-[var(--card)]">{children}</div>}
    </div>
  );
}

export default function PublicKBPage() {
  const params = useParams();
  const slug = params.slug as string;
  const [data, setData] = useState<any>(null);
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        // slug is brand_id
        const [pubRes, cfgRes] = await Promise.all([
          fetch(`${API_URL}/api/brands/${slug}/public`),
          fetch(`${API_URL}/api/brands/${slug}/embed-config`),
        ]);
        if (!pubRes.ok) throw new Error("Not found");
        setData(await pubRes.json());
        if (cfgRes.ok) setConfig(await cfgRes.json());
      } catch {
        setError("Knowledge base not found");
      }
      setLoading(false);
    };
    load();
  }, [slug]);

  if (loading) return <div className="flex justify-center py-20"><div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" /></div>;
  if (error || !data) return <div className="text-center py-20 text-[var(--muted-foreground)]">{error || "Not found"}</div>;

  const d = data.data;
  const identity = d?.identity;
  const offerings = d?.offerings;
  const trust = d?.trust;
  const access = d?.access;
  const campaigns = d?.campaigns;

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      {/* Hero */}
      <div className="text-center mb-10">
        <div className="w-20 h-20 rounded-2xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mx-auto mb-4">
          <Globe className="w-10 h-10 text-primary-600" />
        </div>
        <h1 className="text-4xl font-extrabold mb-2">{data.name || identity?.name || "Brand"}</h1>
        {identity?.tagline && <p className="text-lg text-primary-600 italic">&ldquo;{identity.tagline}&rdquo;</p>}
        {identity?.positioning && <p className="mt-3 text-[var(--muted-foreground)] max-w-2xl mx-auto">{identity.positioning}</p>}
      </div>

      {/* Sections */}
      <div className="space-y-4">
        {identity && (
          <Accordion title="关于" icon={Globe} defaultOpen>
            <div className="space-y-3 text-sm">
              {identity.mission && <p><strong>使命：</strong> {identity.mission}</p>}
              {identity.vision && <p><strong>愿景：</strong> {identity.vision}</p>}
              {identity.brand_story && <p>{identity.brand_story}</p>}
              <div className="grid grid-cols-2 gap-3">
                {identity.founded && <div><span className="text-xs text-[var(--muted-foreground)]">创立时间</span><div>{identity.founded}</div></div>}
                {identity.headquarters && <div><span className="text-xs text-[var(--muted-foreground)]">总部</span><div>{identity.headquarters}</div></div>}
                {identity.category && <div><span className="text-xs text-[var(--muted-foreground)]">行业</span><div>{identity.category}</div></div>}
                {identity.scale && <div><span className="text-xs text-[var(--muted-foreground)]">规模</span><div>{identity.scale}</div></div>}
              </div>
              {identity.values?.length > 0 && (
                <div className="flex flex-wrap gap-2">{identity.values.map((v: string, i: number) => <span key={i} className="px-3 py-1 rounded-full text-xs bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300">{v}</span>)}</div>
              )}
            </div>
          </Accordion>
        )}

        {offerings?.length > 0 && (
          <Accordion title={`产品服务 (${offerings.length})`} icon={Package}>
            <div className="grid sm:grid-cols-2 gap-3">
              {offerings.map((item: any, i: number) => (
                <div key={i} className="p-3 rounded-lg bg-[var(--muted)]">
                  <h4 className="font-medium text-sm">{item.name}</h4>
                  {item.description && <p className="text-xs text-[var(--muted-foreground)] mt-1">{item.description}</p>}
                </div>
              ))}
            </div>
          </Accordion>
        )}

        {trust && (
          <Accordion title="信任背书" icon={Shield}>
            <div className="space-y-3 text-sm">
              {trust.certifications?.length > 0 && <div className="flex flex-wrap gap-2">{trust.certifications.map((c: string, i: number) => <span key={i} className="px-2 py-1 rounded-full text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">{c}</span>)}</div>}
              {trust.partnerships?.length > 0 && <div><strong>合作伙伴：</strong> {trust.partnerships.join(", ")}</div>}
              {trust.testimonials?.length > 0 && trust.testimonials.map((t: any, i: number) => <blockquote key={i} className="border-l-2 border-primary-600 pl-3 italic text-[var(--muted-foreground)]">&ldquo;{t.quote}&rdquo; — {t.source}</blockquote>)}
            </div>
          </Accordion>
        )}

        {access && (
          <Accordion title="联系方式" icon={Globe}>
            <div className="text-sm space-y-2">
              {access.official_website && <a href={access.official_website} target="_blank" rel="noopener" className="text-primary-600 hover:underline block">{access.official_website}</a>}
              {access.contact?.email && <p>Email: {access.contact.email}</p>}
              {access.contact?.phone && <p>Phone: {access.contact.phone}</p>}
              {access.contact?.address && <p>Address: {access.contact.address}</p>}
            </div>
          </Accordion>
        )}

        {campaigns && (campaigns.ongoing?.length > 0 || campaigns.recent?.length > 0 || campaigns.upcoming?.length > 0 || campaigns.annual_events?.length > 0) && (
          <Accordion title="品牌活动" icon={Calendar}>
            <div className="space-y-3 text-sm">
              {campaigns.ongoing?.length > 0 && (
                <div>
                  <h4 className="font-medium mb-1">进行中</h4>
                  {campaigns.ongoing.map((c: any, i: number) => (
                    <div key={i} className="mb-2 p-2 rounded bg-green-50 dark:bg-green-900/10">
                      <span className="font-medium">{c.name}</span>
                      {c.type && <span className="ml-2 text-xs text-[var(--muted-foreground)]">{c.type}</span>}
                      {c.description && <p className="text-xs text-[var(--muted-foreground)] mt-1">{c.description}</p>}
                    </div>
                  ))}
                </div>
              )}
              {campaigns.recent?.length > 0 && (
                <div>
                  <h4 className="font-medium mb-1">近期活动</h4>
                  {campaigns.recent.map((c: any, i: number) => (
                    <div key={i} className="mb-2"><span className="font-medium">{c.name}</span>{c.date && <span className="ml-2 text-xs text-[var(--muted-foreground)]">{c.date}</span>}{c.impact && <p className="text-xs text-[var(--muted-foreground)]">效果：{c.impact}</p>}</div>
                  ))}
                </div>
              )}
              {campaigns.upcoming?.length > 0 && (
                <div>
                  <h4 className="font-medium mb-1">即将到来</h4>
                  {campaigns.upcoming.map((c: any, i: number) => (
                    <div key={i} className="mb-2"><span className="font-medium">{c.name}</span><span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700">即将开始</span>{c.preview && <p className="text-xs text-[var(--muted-foreground)] mt-1">{c.preview}</p>}</div>
                  ))}
                </div>
              )}
              {campaigns.annual_events?.length > 0 && (
                <div>
                  <h4 className="font-medium mb-1">年度活动</h4>
                  {campaigns.annual_events.map((c: any, i: number) => (
                    <div key={i} className="mb-2"><span className="font-medium">{c.name}</span>{c.frequency && <span className="ml-2 text-xs text-[var(--muted-foreground)]">{c.frequency}</span>}</div>
                  ))}
                </div>
              )}
            </div>
          </Accordion>
        )}
      </div>
      {config && (
        <div className="mt-10 p-6 rounded-2xl border border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-950/20">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary-600" />
            将此知识库接入 AI
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-[var(--muted-foreground)]">MCP Endpoint</label>
              <div className="flex items-center gap-2 mt-1">
                <code className="flex-1 text-sm px-3 py-2 rounded-lg bg-white dark:bg-[var(--card)] truncate">{config.mcp_endpoint}</code>
                <CopyBtn text={config.mcp_endpoint} />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-[var(--muted-foreground)]">API Endpoint</label>
              <div className="flex items-center gap-2 mt-1">
                <code className="flex-1 text-sm px-3 py-2 rounded-lg bg-white dark:bg-[var(--card)] truncate">{config.api_endpoint}</code>
                <CopyBtn text={config.api_endpoint} />
              </div>
            </div>
            <div className="text-sm text-[var(--muted-foreground)] space-y-1">
              <p><strong>快速开始：</strong></p>
              {config.instructions?.map((s: string, i: number) => <p key={i}>{s}</p>)}
            </div>
          </div>
        </div>
      )}

      {/* Footer badge */}
      <div className="mt-10 text-center">
        <a href="/" className="inline-flex items-center gap-1 text-xs text-[var(--muted-foreground)] hover:text-primary-600 transition">
          <Zap className="w-3 h-3" /> Powered by Brand2Context
        </a>
      </div>
    </div>
  );
}
