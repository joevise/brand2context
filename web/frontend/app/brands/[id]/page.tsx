"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getBrand, getBrandStatus, Brand } from "@/lib/api";
import {
  Building2, Package, Sparkles, Shield, MessageCircle, MapPin,
  Newspaper, Eye, BarChart3, Activity, Loader2, ArrowLeft, ExternalLink,
  Star, Award, Users, Globe, Mail, Phone
} from "lucide-react";
import Link from "next/link";

function Section({ title, icon: Icon, children, color = "primary" }: any) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] overflow-hidden">
      <div className="px-6 py-4 border-b border-[var(--border)] bg-[var(--muted)]">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Icon className="w-5 h-5 text-primary-600" />
          {title}
        </h2>
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="inline-block px-3 py-1 rounded-full text-sm bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300">{children}</span>;
}

function KV({ label, value }: { label: string; value: any }) {
  if (!value) return null;
  return (
    <div>
      <dt className="text-xs font-medium text-[var(--muted-foreground)] uppercase tracking-wide">{label}</dt>
      <dd className="mt-1">{typeof value === "string" ? value : JSON.stringify(value)}</dd>
    </div>
  );
}

function IdentityCard({ data }: { data: any }) {
  if (!data) return null;
  return (
    <Section title="Identity" icon={Building2}>
      <div className="space-y-6">
        <div>
          <h3 className="text-2xl font-bold mb-1">{data.name}</h3>
          {data.tagline && <p className="text-lg text-primary-600 italic">&ldquo;{data.tagline}&rdquo;</p>}
        </div>
        {data.positioning && (
          <p className="text-[var(--muted-foreground)] leading-relaxed">{data.positioning}</p>
        )}
        <div className="grid sm:grid-cols-2 gap-4">
          <KV label="Legal Name" value={data.legal_name} />
          <KV label="Founded" value={data.founded} />
          <KV label="Headquarters" value={data.headquarters} />
          <KV label="Category" value={data.category} />
          <KV label="Founder" value={data.founder} />
          <KV label="Scale" value={data.scale} />
        </div>
        {data.mission && <div className="p-4 rounded-xl bg-[var(--muted)]"><p className="text-sm"><strong>Mission:</strong> {data.mission}</p></div>}
        {data.vision && <div className="p-4 rounded-xl bg-[var(--muted)]"><p className="text-sm"><strong>Vision:</strong> {data.vision}</p></div>}
        {data.values?.length > 0 && (
          <div><h4 className="text-sm font-medium mb-2">Values</h4><div className="flex flex-wrap gap-2">{data.values.map((v: string, i: number) => <Tag key={i}>{v}</Tag>)}</div></div>
        )}
        {data.brand_story && <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">{data.brand_story}</p>}
      </div>
    </Section>
  );
}

function OfferingsGrid({ data }: { data: any[] }) {
  if (!data?.length) return null;
  return (
    <Section title={`Offerings (${data.length})`} icon={Package}>
      <div className="grid sm:grid-cols-2 gap-4">
        {data.map((item, i) => (
          <div key={i} className="p-4 rounded-xl border border-[var(--border)] hover:shadow-md transition">
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-semibold">{item.name}</h4>
              {item.is_flagship && <Star className="w-4 h-4 text-yellow-500 flex-shrink-0" />}
            </div>
            {item.category && <p className="text-xs text-primary-600 mb-2">{item.category}</p>}
            <p className="text-sm text-[var(--muted-foreground)] mb-3">{item.description}</p>
            {item.key_features?.length > 0 && (
              <ul className="text-xs text-[var(--muted-foreground)] space-y-1">
                {item.key_features.slice(0, 4).map((f: string, j: number) => (
                  <li key={j} className="flex items-start gap-1"><span className="text-primary-600 mt-0.5">•</span>{f}</li>
                ))}
              </ul>
            )}
            {item.price_range && <p className="mt-2 text-sm font-medium">{item.price_range}</p>}
          </div>
        ))}
      </div>
    </Section>
  );
}

function DifferentiationSection({ data }: { data: any }) {
  if (!data) return null;
  return (
    <Section title="Differentiation" icon={Sparkles}>
      <div className="space-y-4">
        {data.unique_selling_points?.length > 0 && (
          <div><h4 className="text-sm font-medium mb-2">Unique Selling Points</h4>{data.unique_selling_points.map((p: string, i: number) => <div key={i} className="flex items-start gap-2 mb-2"><Sparkles className="w-4 h-4 text-primary-600 mt-0.5 flex-shrink-0" /><span className="text-sm">{p}</span></div>)}</div>
        )}
        {data.competitive_advantages?.length > 0 && (
          <div><h4 className="text-sm font-medium mb-2">Competitive Advantages</h4><div className="flex flex-wrap gap-2">{data.competitive_advantages.map((a: string, i: number) => <Tag key={i}>{a}</Tag>)}</div></div>
        )}
        {data.technology_highlights?.length > 0 && (
          <div><h4 className="text-sm font-medium mb-2">Technology</h4><ul className="space-y-1 text-sm">{data.technology_highlights.map((t: string, i: number) => <li key={i}>• {t}</li>)}</ul></div>
        )}
        {data.awards?.length > 0 && (
          <div><h4 className="text-sm font-medium mb-2">Awards</h4>{data.awards.map((a: any, i: number) => <div key={i} className="flex items-center gap-2 text-sm"><Award className="w-4 h-4 text-yellow-500" />{a.name} {a.year && `(${a.year})`}</div>)}</div>
        )}
      </div>
    </Section>
  );
}

function TrustSection({ data }: { data: any }) {
  if (!data) return null;
  return (
    <Section title="Trust Signals" icon={Shield}>
      <div className="space-y-4">
        {data.certifications?.length > 0 && <div><h4 className="text-sm font-medium mb-2">Certifications</h4><div className="flex flex-wrap gap-2">{data.certifications.map((c: string, i: number) => <Tag key={i}>{c}</Tag>)}</div></div>}
        {data.partnerships?.length > 0 && <div><h4 className="text-sm font-medium mb-2">Partnerships</h4><div className="flex flex-wrap gap-2">{data.partnerships.map((p: string, i: number) => <Tag key={i}>{p}</Tag>)}</div></div>}
        {data.user_stats?.length > 0 && <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">{data.user_stats.map((s: any, i: number) => <div key={i} className="p-3 rounded-xl bg-[var(--muted)] text-center"><div className="text-lg font-bold text-primary-600">{s.value}</div><div className="text-xs text-[var(--muted-foreground)]">{s.metric}</div></div>)}</div>}
        {data.testimonials?.length > 0 && <div className="space-y-3">{data.testimonials.map((t: any, i: number) => <blockquote key={i} className="border-l-2 border-primary-600 pl-4 italic text-sm text-[var(--muted-foreground)]">&ldquo;{t.quote}&rdquo; — {t.source}</blockquote>)}</div>}
      </div>
    </Section>
  );
}

function ExperienceSection({ data }: { data: any }) {
  if (!data) return null;
  return (
    <Section title="Experience & FAQ" icon={MessageCircle}>
      <div className="space-y-4">
        <div className="grid sm:grid-cols-2 gap-4">
          <KV label="Warranty" value={data.warranty} />
          <KV label="Return Policy" value={data.return_policy} />
          <KV label="Onboarding" value={data.onboarding} />
          <KV label="Community" value={data.community} />
        </div>
        {data.faq?.length > 0 && (
          <div><h4 className="text-sm font-medium mb-3">FAQ</h4><div className="space-y-3">{data.faq.map((f: any, i: number) => <details key={i} className="group"><summary className="cursor-pointer font-medium text-sm hover:text-primary-600">{f.question}</summary><p className="mt-2 text-sm text-[var(--muted-foreground)] pl-4">{f.answer}</p></details>)}</div></div>
        )}
      </div>
    </Section>
  );
}

function AccessSection({ data }: { data: any }) {
  if (!data) return null;
  return (
    <Section title="Access & Contact" icon={MapPin}>
      <div className="space-y-4">
        {data.official_website && <a href={data.official_website} target="_blank" rel="noopener" className="inline-flex items-center gap-2 text-primary-600 hover:underline"><Globe className="w-4 h-4" />{data.official_website}</a>}
        {data.contact && (
          <div className="grid sm:grid-cols-2 gap-3">
            {data.contact.email && <div className="flex items-center gap-2 text-sm"><Mail className="w-4 h-4 text-[var(--muted-foreground)]" />{data.contact.email}</div>}
            {data.contact.phone && <div className="flex items-center gap-2 text-sm"><Phone className="w-4 h-4 text-[var(--muted-foreground)]" />{data.contact.phone}</div>}
            {data.contact.address && <div className="flex items-center gap-2 text-sm sm:col-span-2"><MapPin className="w-4 h-4 text-[var(--muted-foreground)]" />{data.contact.address}</div>}
          </div>
        )}
        {data.social_media?.length > 0 && <div className="flex flex-wrap gap-2">{data.social_media.map((s: any, i: number) => <a key={i} href={s.url} target="_blank" rel="noopener" className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-[var(--muted)] text-sm hover:bg-primary-100 dark:hover:bg-primary-900/30 transition"><ExternalLink className="w-3 h-3" />{s.platform}</a>)}</div>}
      </div>
    </Section>
  );
}

function ContentSection({ data }: { data: any }) {
  if (!data) return null;
  const news = [...(data.latest_news || []), ...(data.key_announcements || [])];
  if (news.length === 0 && !data.blog_posts?.length) return null;
  return (
    <Section title="Content & News" icon={Newspaper}>
      <div className="space-y-3">
        {news.map((n: any, i: number) => (
          <div key={i} className="p-3 rounded-xl bg-[var(--muted)]">
            <div className="flex items-start justify-between">
              <h4 className="font-medium text-sm">{n.title}</h4>
              {n.date && <span className="text-xs text-[var(--muted-foreground)] flex-shrink-0 ml-2">{n.date}</span>}
            </div>
            {(n.summary || n.content) && <p className="text-xs text-[var(--muted-foreground)] mt-1">{n.summary || n.content}</p>}
          </div>
        ))}
      </div>
    </Section>
  );
}

function PerceptionSection({ data }: { data: any }) {
  if (!data) return null;
  return (
    <Section title="Perception" icon={Eye}>
      <div className="space-y-4">
        {data.personality_traits?.length > 0 && <div className="flex flex-wrap gap-2">{data.personality_traits.map((t: string, i: number) => <Tag key={i}>{t}</Tag>)}</div>}
        <div className="grid sm:grid-cols-2 gap-4">
          <KV label="Brand Tone" value={data.brand_tone} />
          <KV label="Price Positioning" value={data.price_positioning} />
          <KV label="Price Benchmark" value={data.price_benchmark} />
          <KV label="Category Association" value={data.category_association} />
        </div>
        {data.primary_audience && (
          <div className="p-4 rounded-xl bg-[var(--muted)]">
            <h4 className="text-sm font-medium mb-2 flex items-center gap-1"><Users className="w-4 h-4" /> Primary Audience</h4>
            <div className="text-sm space-y-1">
              {data.primary_audience.demographics && <p><strong>Demographics:</strong> {data.primary_audience.demographics}</p>}
              {data.primary_audience.psychographics && <p><strong>Psychographics:</strong> {data.primary_audience.psychographics}</p>}
              {data.primary_audience.lifestyle && <p><strong>Lifestyle:</strong> {data.primary_audience.lifestyle}</p>}
            </div>
          </div>
        )}
        {data.usage_occasions?.length > 0 && <div><h4 className="text-sm font-medium mb-2">Usage Occasions</h4><div className="flex flex-wrap gap-2">{data.usage_occasions.map((o: string, i: number) => <Tag key={i}>{o}</Tag>)}</div></div>}
      </div>
    </Section>
  );
}

function DecisionSection({ data }: { data: any }) {
  if (!data) return null;
  return (
    <Section title="Decision Factors" icon={BarChart3}>
      <div className="space-y-4">
        {data.category_key_factors?.length > 0 && (
          <div className="space-y-2">
            {data.category_key_factors.map((f: any, i: number) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-[var(--muted)]">
                <div className="flex-1">
                  <div className="font-medium text-sm">{f.factor}</div>
                  {f.evidence && <div className="text-xs text-[var(--muted-foreground)] mt-0.5">{f.evidence}</div>}
                </div>
                {f.brand_score && <span className="px-2 py-1 rounded-lg bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-sm font-medium">{f.brand_score}</span>}
              </div>
            ))}
          </div>
        )}
        {data.perceived_risks?.length > 0 && (
          <div><h4 className="text-sm font-medium mb-2">Perceived Risks</h4>{data.perceived_risks.map((r: any, i: number) => <div key={i} className="mb-2"><p className="text-sm font-medium text-red-500">⚠ {r.risk}</p>{r.mitigation && <p className="text-xs text-[var(--muted-foreground)] ml-4">→ {r.mitigation}</p>}</div>)}</div>
        )}
        <div className="grid sm:grid-cols-2 gap-4">
          <KV label="Switching Cost" value={data.switching_cost} />
          <KV label="Trial Barrier" value={data.trial_barrier} />
        </div>
      </div>
    </Section>
  );
}

function VitalitySection({ data }: { data: any }) {
  if (!data) return null;
  return (
    <Section title="Vitality" icon={Activity}>
      <div className="grid sm:grid-cols-2 gap-4">
        <KV label="Content Frequency" value={data.content_frequency} />
        <KV label="Last Product Launch" value={data.last_product_launch} />
        <KV label="Last Campaign" value={data.last_campaign} />
        <KV label="Growth Signal" value={data.growth_signal} />
        <KV label="Community Size" value={data.community_size} />
        <KV label="NPS / Satisfaction" value={data.nps_or_satisfaction} />
        <KV label="Market Position" value={data.market_position} />
        <KV label="Industry Role" value={data.industry_role} />
      </div>
    </Section>
  );
}

export default function BrandDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [brand, setBrand] = useState<Brand | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let interval: any;

    const load = async () => {
      try {
        const data = await getBrand(id);
        setBrand(data);
        setLoading(false);

        if (data.status === "pending" || data.status === "processing") {
          interval = setInterval(async () => {
            const status = await getBrandStatus(id);
            if (status.status === "done" || status.status === "error") {
              clearInterval(interval);
              const updated = await getBrand(id);
              setBrand(updated);
            }
          }, 3000);
        }
      } catch {
        setLoading(false);
      }
    };

    load();
    return () => interval && clearInterval(interval);
  }, [id]);

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div>;
  if (!brand) return <div className="text-center py-20">Brand not found</div>;

  const isGenerating = brand.status === "pending" || brand.status === "processing";
  const d = brand.data;

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <Link href="/brands" className="inline-flex items-center gap-1 text-sm text-[var(--muted-foreground)] hover:text-primary-600 mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to brands
      </Link>

      {isGenerating && (
        <div className="mb-8 p-8 rounded-2xl border border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-950/20 text-center">
          <Loader2 className="w-10 h-10 animate-spin text-primary-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Generating Brand Knowledge Base</h2>
          <p className="text-[var(--muted-foreground)]">Crawling {brand.url} and structuring data...</p>
          <p className="text-xs text-[var(--muted-foreground)] mt-2">This usually takes 1-3 minutes</p>
        </div>
      )}

      {brand.status === "error" && (
        <div className="mb-8 p-6 rounded-2xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/20">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Generation Failed</h2>
          <p className="text-sm text-red-500">{brand.error_message || "Unknown error"}</p>
        </div>
      )}

      {d && (
        <div className="space-y-6">
          <IdentityCard data={d.identity} />
          <OfferingsGrid data={d.offerings} />
          <DifferentiationSection data={d.differentiation} />
          <TrustSection data={d.trust} />
          <ExperienceSection data={d.experience} />
          <AccessSection data={d.access} />
          <ContentSection data={d.content} />
          <PerceptionSection data={d.perception} />
          <DecisionSection data={d.decision_factors} />
          <VitalitySection data={d.vitality} />
        </div>
      )}
    </div>
  );
}
