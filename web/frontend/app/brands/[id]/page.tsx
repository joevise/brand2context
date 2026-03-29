"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import { getBrand, getBrandStatus, updateKnowledge, searchBrand, Brand } from "@/lib/api";
import {
  Building2, Package, Sparkles, Shield, MessageCircle, MapPin,
  Newspaper, Eye, BarChart3, Activity, Loader2, ArrowLeft, ExternalLink,
  Star, Award, Users, Globe, Mail, Phone, Pencil, Save, XCircle, Check,
  Search, Plus, Trash2, X
} from "lucide-react";
import Link from "next/link";
import { ChatPanel } from "@/components/chat-panel";
import { IntegrationPanel } from "@/components/integration-panel";

function Section({ title, icon: Icon, children, editMode, onEdit }: any) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] overflow-hidden">
      <div className="px-6 py-4 border-b border-[var(--border)] bg-[var(--muted)] flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Icon className="w-5 h-5 text-primary-600" />
          {title}
        </h2>
        {editMode && onEdit && (
          <button onClick={onEdit} className="p-1.5 rounded-lg hover:bg-primary-100 dark:hover:bg-primary-900/30 text-primary-600 transition">
            <Pencil className="w-4 h-4" />
          </button>
        )}
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

// Inline edit modal
function EditModal({ title, value, onSave, onCancel }: { title: string; value: string; onSave: (v: string) => void; onCancel: () => void }) {
  const [text, setText] = useState(value);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onCancel}>
      <div className="bg-[var(--card)] rounded-2xl p-6 w-full max-w-lg mx-4 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold mb-4">Edit {title}</h3>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="w-full h-40 px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] text-sm focus:outline-none focus:ring-2 focus:ring-primary-600 resize-none"
        />
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onCancel} className="px-4 py-2 rounded-lg text-sm hover:bg-[var(--muted)] transition">Cancel</button>
          <button onClick={() => onSave(text)} className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm hover:bg-primary-700 transition flex items-center gap-1">
            <Save className="w-3 h-3" /> Save
          </button>
        </div>
      </div>
    </div>
  );
}

// Edit array of strings modal
function EditArrayModal({ title, values, onSave, onCancel }: { title: string; values: string[]; onSave: (v: string[]) => void; onCancel: () => void }) {
  const [items, setItems] = useState<string[]>([...(values || [])]);
  const add = () => setItems([...items, ""]);
  const remove = (i: number) => setItems(items.filter((_, idx) => idx !== i));
  const update = (i: number, v: string) => { const n = [...items]; n[i] = v; setItems(n); };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onCancel}>
      <div className="bg-[var(--card)] rounded-2xl p-6 w-full max-w-lg mx-4 shadow-2xl max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold mb-4">Edit {title}</h3>
        <div className="space-y-2">
          {items.map((item, i) => (
            <div key={i} className="flex gap-2">
              <input value={item} onChange={(e) => update(i, e.target.value)} className="flex-1 px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] text-sm focus:outline-none focus:ring-2 focus:ring-primary-600" />
              <button onClick={() => remove(i)} className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
        <button onClick={add} className="mt-3 inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-[var(--muted)] hover:bg-primary-100 dark:hover:bg-primary-900/30 transition"><Plus className="w-3 h-3" /> Add Item</button>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onCancel} className="px-4 py-2 rounded-lg text-sm hover:bg-[var(--muted)] transition">Cancel</button>
          <button onClick={() => onSave(items.filter(Boolean))} className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm hover:bg-primary-700 transition flex items-center gap-1"><Save className="w-3 h-3" /> Save</button>
        </div>
      </div>
    </div>
  );
}

// Edit object with multiple fields
function EditObjectModal({ title, fields, values, onSave, onCancel }: { title: string; fields: { key: string; label: string }[]; values: Record<string, string>; onSave: (v: Record<string, string>) => void; onCancel: () => void }) {
  const [data, setData] = useState<Record<string, string>>({ ...values });
  const update = (key: string, v: string) => setData({ ...data, [key]: v });
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onCancel}>
      <div className="bg-[var(--card)] rounded-2xl p-6 w-full max-w-lg mx-4 shadow-2xl max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold mb-4">Edit {title}</h3>
        <div className="space-y-3">
          {fields.map((f) => (
            <div key={f.key}>
              <label className="text-xs font-medium text-[var(--muted-foreground)] uppercase tracking-wide">{f.label}</label>
              <input value={data[f.key] || ""} onChange={(e) => update(f.key, e.target.value)} className="w-full mt-1 px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] text-sm focus:outline-none focus:ring-2 focus:ring-primary-600" />
            </div>
          ))}
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onCancel} className="px-4 py-2 rounded-lg text-sm hover:bg-[var(--muted)] transition">Cancel</button>
          <button onClick={() => onSave(data)} className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm hover:bg-primary-700 transition flex items-center gap-1"><Save className="w-3 h-3" /> Save</button>
        </div>
      </div>
    </div>
  );
}

// Edit array of objects
function EditObjectArrayModal({ title, fields, values, onSave, onCancel }: { title: string; fields: { key: string; label: string }[]; values: Record<string, any>[]; onSave: (v: Record<string, any>[]) => void; onCancel: () => void }) {
  const [items, setItems] = useState<Record<string, any>[]>(values?.map(v => ({ ...v })) || []);
  const add = () => { const empty: Record<string, any> = {}; fields.forEach(f => empty[f.key] = ""); setItems([...items, empty]); };
  const remove = (i: number) => setItems(items.filter((_, idx) => idx !== i));
  const update = (i: number, key: string, v: string) => { const n = [...items]; n[i] = { ...n[i], [key]: v }; setItems(n); };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onCancel}>
      <div className="bg-[var(--card)] rounded-2xl p-6 w-full max-w-lg mx-4 shadow-2xl max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold mb-4">Edit {title}</h3>
        <div className="space-y-4">
          {items.map((item, i) => (
            <div key={i} className="p-3 rounded-xl border border-[var(--border)] space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs font-medium text-[var(--muted-foreground)]">#{i + 1}</span>
                <button onClick={() => remove(i)} className="p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"><Trash2 className="w-3 h-3" /></button>
              </div>
              {fields.map((f) => (
                <div key={f.key}>
                  <label className="text-xs text-[var(--muted-foreground)]">{f.label}</label>
                  <input value={item[f.key] || ""} onChange={(e) => update(i, f.key, e.target.value)} className="w-full mt-0.5 px-2 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--background)] text-sm focus:outline-none focus:ring-2 focus:ring-primary-600" />
                </div>
              ))}
            </div>
          ))}
        </div>
        <button onClick={add} className="mt-3 inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-[var(--muted)] hover:bg-primary-100 dark:hover:bg-primary-900/30 transition"><Plus className="w-3 h-3" /> Add Item</button>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onCancel} className="px-4 py-2 rounded-lg text-sm hover:bg-[var(--muted)] transition">Cancel</button>
          <button onClick={() => onSave(items)} className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm hover:bg-primary-700 transition flex items-center gap-1"><Save className="w-3 h-3" /> Save</button>
        </div>
      </div>
    </div>
  );
}

// Editable field wrapper — shows pencil on hover when in edit mode
function EditableField({ editMode, onClick, children }: { editMode: boolean; onClick?: () => void; children: React.ReactNode }) {
  if (!editMode) return <>{children}</>;
  return (
    <div className="group relative cursor-pointer" onClick={onClick}>
      {children}
      <Pencil className="w-3 h-3 absolute top-0 right-0 opacity-0 group-hover:opacity-100 text-primary-600 transition" />
    </div>
  );
}

// Knowledge Base Search Bar
function KBSearchBar({ brandId }: { brandId: string }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ documents: string[]; metadatas: any[] } | null>(null);
  const [searching, setSearching] = useState(false);
  const [open, setOpen] = useState(false);

  const DIMENSION_LABELS: Record<string, string> = {
    identity: "Identity", offerings: "Offerings", differentiation: "Differentiation",
    trust: "Trust Signals", experience: "Experience", access: "Access & Contact",
    content: "Content & News", perception: "Perception", decision_factors: "Decision Factors", vitality: "Vitality",
  };

  const doSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setOpen(true);
    try {
      const res = await searchBrand(brandId, query);
      setResults(res);
    } catch {
      setResults({ documents: [], metadatas: [] });
    } finally {
      setSearching(false);
    }
  };

  const scrollToSection = (dimension: string) => {
    const label = DIMENSION_LABELS[dimension];
    if (!label) return;
    const headings = Array.from(document.querySelectorAll("h2"));
    for (let i = 0; i < headings.length; i++) {
      if (headings[i].textContent?.includes(label)) {
        headings[i].scrollIntoView({ behavior: "smooth", block: "start" });
        setOpen(false);
        break;
      }
    }
  };

  return (
    <div className="relative mb-6">
      <form onSubmit={(e) => { e.preventDefault(); doSearch(); }} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--muted-foreground)]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search this knowledge base..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--card)] text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
          />
        </div>
        <button type="submit" disabled={searching || !query.trim()} className="px-4 py-2 rounded-xl bg-primary-600 text-white text-sm hover:bg-primary-700 disabled:opacity-50 transition">
          {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : "Search"}
        </button>
      </form>
      {open && results && (
        <div className="absolute top-full left-0 right-0 mt-2 z-40 rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-xl max-h-80 overflow-y-auto">
          <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border)]">
            <span className="text-xs text-[var(--muted-foreground)]">{results.documents.length} result{results.documents.length !== 1 ? "s" : ""}</span>
            <button onClick={() => setOpen(false)} className="p-1 hover:bg-[var(--muted)] rounded"><X className="w-3 h-3" /></button>
          </div>
          {results.documents.length === 0 && <div className="p-4 text-sm text-[var(--muted-foreground)] text-center">No results found</div>}
          {results.documents.map((doc, i) => {
            const meta = results.metadatas?.[i] || {};
            const dim = meta.dimension || "unknown";
            // Strip the [brand] [dim] prefix for display
            const text = doc.replace(/^\[.*?\]\s*\[.*?\]\s*/, "").slice(0, 200);
            return (
              <button key={i} onClick={() => scrollToSection(dim)} className="w-full text-left px-4 py-3 border-b border-[var(--border)] last:border-0 hover:bg-[var(--muted)] transition">
                <span className="inline-block px-2 py-0.5 rounded-full text-xs bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 mb-1">{DIMENSION_LABELS[dim] || dim}</span>
                <p className="text-sm text-[var(--muted-foreground)] line-clamp-2">{text}...</p>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function IdentityCard({ data, editMode, onUpdate }: { data: any; editMode: boolean; onUpdate: (section: string, data: any) => void }) {
  const [editing, setEditing] = useState<string | null>(null);
  const [editingArray, setEditingArray] = useState<string | null>(null);
  const [editingObj, setEditingObj] = useState<string | null>(null);
  if (!data) return null;

  const handleSave = (field: string, value: string) => {
    onUpdate("identity", { [field]: value });
    setEditing(null);
  };

  const handleArraySave = (field: string, values: string[]) => {
    onUpdate("identity", { [field]: values });
    setEditingArray(null);
  };

  const handleObjSave = (field: string, values: Record<string, string>) => {
    onUpdate("identity", { [field]: values });
    setEditingObj(null);
  };

  return (
    <Section title="Identity" icon={Building2} editMode={editMode}>
      {editing && (
        <EditModal title={editing} value={data[editing] || ""} onSave={(v) => handleSave(editing, v)} onCancel={() => setEditing(null)} />
      )}
      {editingArray === "values" && (
        <EditArrayModal title="Values" values={data.values || []} onSave={(v) => handleArraySave("values", v)} onCancel={() => setEditingArray(null)} />
      )}
      <div className="space-y-6">
        <div>
          <EditableField editMode={editMode} onClick={() => setEditing("name")}>
            <h3 className="text-2xl font-bold mb-1">{data.name}</h3>
          </EditableField>
          {data.tagline && (
            <EditableField editMode={editMode} onClick={() => setEditing("tagline")}>
              <p className="text-lg text-primary-600 italic">&ldquo;{data.tagline}&rdquo;</p>
            </EditableField>
          )}
        </div>
        {data.positioning && (
          <EditableField editMode={editMode} onClick={() => setEditing("positioning")}>
            <p className="text-[var(--muted-foreground)] leading-relaxed">{data.positioning}</p>
          </EditableField>
        )}
        <div className="grid sm:grid-cols-2 gap-4">
          {["legal_name", "founded", "headquarters", "category", "founder", "scale"].map((field) => (
            <EditableField key={field} editMode={editMode} onClick={() => setEditing(field)}>
              <KV label={field.replace("_", " ")} value={data[field]} />
            </EditableField>
          ))}
        </div>
        {data.mission && (
          <EditableField editMode={editMode} onClick={() => setEditing("mission")}>
            <div className="p-4 rounded-xl bg-[var(--muted)]"><p className="text-sm"><strong>Mission:</strong> {data.mission}</p></div>
          </EditableField>
        )}
        {data.vision && (
          <EditableField editMode={editMode} onClick={() => setEditing("vision")}>
            <div className="p-4 rounded-xl bg-[var(--muted)]"><p className="text-sm"><strong>Vision:</strong> {data.vision}</p></div>
          </EditableField>
        )}
        {(data.values?.length > 0 || editMode) && (
          <EditableField editMode={editMode} onClick={() => setEditingArray("values")}>
            <div><h4 className="text-sm font-medium mb-2">Values</h4><div className="flex flex-wrap gap-2">{(data.values || []).map((v: string, i: number) => <Tag key={i}>{v}</Tag>)}</div></div>
          </EditableField>
        )}
        {data.brand_story && (
          <EditableField editMode={editMode} onClick={() => setEditing("brand_story")}>
            <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">{data.brand_story}</p>
          </EditableField>
        )}
      </div>
    </Section>
  );
}

function OfferingsGrid({ data, editMode, onUpdate }: { data: any[]; editMode: boolean; onUpdate: (section: string, data: any) => void }) {
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  if (!data?.length && !editMode) return null;
  const items = data || [];

  const handleSave = (values: Record<string, any>[]) => {
    // Convert key_features back from comma-separated string to array
    const processed = values.map(v => ({
      ...v,
      key_features: typeof v.key_features === "string" ? v.key_features.split(",").map((s: string) => s.trim()).filter(Boolean) : v.key_features,
      is_flagship: v.is_flagship === "true" || v.is_flagship === true,
    }));
    onUpdate("offerings", processed);
    setEditingIdx(null);
  };

  return (
    <Section title={`Offerings (${items.length})`} icon={Package} editMode={editMode} onEdit={() => setEditingIdx(0)}>
      {editingIdx !== null && (
        <EditObjectArrayModal
          title="Offerings"
          fields={[
            { key: "name", label: "Name" },
            { key: "category", label: "Category" },
            { key: "description", label: "Description" },
            { key: "key_features", label: "Key Features (comma separated)" },
            { key: "price_range", label: "Price Range" },
            { key: "is_flagship", label: "Flagship (true/false)" },
          ]}
          values={items.map(item => ({ ...item, key_features: item.key_features?.join(", ") || "", is_flagship: String(!!item.is_flagship) }))}
          onSave={handleSave}
          onCancel={() => setEditingIdx(null)}
        />
      )}
      <div className="grid sm:grid-cols-2 gap-4">
        {items.map((item, i) => (
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

function DifferentiationSection({ data, editMode, onUpdate }: { data: any; editMode: boolean; onUpdate: (section: string, data: any) => void }) {
  if (!data) return null;
  const [editField, setEditField] = useState<string | null>(null);
  const [editObjArr, setEditObjArr] = useState<string | null>(null);

  return (
    <Section title="Differentiation" icon={Sparkles} editMode={editMode} onEdit={() => setEditField("unique_selling_points")}>
      {editField === "unique_selling_points" && (
        <EditArrayModal title="Unique Selling Points" values={data.unique_selling_points || []} onSave={(v) => { onUpdate("differentiation", { ...data, unique_selling_points: v }); setEditField(null); }} onCancel={() => setEditField(null)} />
      )}
      {editField === "competitive_advantages" && (
        <EditArrayModal title="Competitive Advantages" values={data.competitive_advantages || []} onSave={(v) => { onUpdate("differentiation", { ...data, competitive_advantages: v }); setEditField(null); }} onCancel={() => setEditField(null)} />
      )}
      {editField === "technology_highlights" && (
        <EditArrayModal title="Technology Highlights" values={data.technology_highlights || []} onSave={(v) => { onUpdate("differentiation", { ...data, technology_highlights: v }); setEditField(null); }} onCancel={() => setEditField(null)} />
      )}
      {editObjArr === "awards" && (
        <EditObjectArrayModal title="Awards" fields={[{ key: "name", label: "Award Name" }, { key: "year", label: "Year" }]} values={data.awards || []} onSave={(v) => { onUpdate("differentiation", { ...data, awards: v }); setEditObjArr(null); }} onCancel={() => setEditObjArr(null)} />
      )}
      <div className="space-y-4">
        {data.unique_selling_points?.length > 0 && (
          <EditableField editMode={editMode} onClick={() => setEditField("unique_selling_points")}>
            <div><h4 className="text-sm font-medium mb-2">Unique Selling Points</h4>{data.unique_selling_points.map((p: string, i: number) => <div key={i} className="flex items-start gap-2 mb-2"><Sparkles className="w-4 h-4 text-primary-600 mt-0.5 flex-shrink-0" /><span className="text-sm">{p}</span></div>)}</div>
          </EditableField>
        )}
        {data.competitive_advantages?.length > 0 && (
          <EditableField editMode={editMode} onClick={() => setEditField("competitive_advantages")}>
            <div><h4 className="text-sm font-medium mb-2">Competitive Advantages</h4><div className="flex flex-wrap gap-2">{data.competitive_advantages.map((a: string, i: number) => <Tag key={i}>{a}</Tag>)}</div></div>
          </EditableField>
        )}
        {data.technology_highlights?.length > 0 && (
          <EditableField editMode={editMode} onClick={() => setEditField("technology_highlights")}>
            <div><h4 className="text-sm font-medium mb-2">Technology</h4><ul className="space-y-1 text-sm">{data.technology_highlights.map((t: string, i: number) => <li key={i}>• {t}</li>)}</ul></div>
          </EditableField>
        )}
        {data.awards?.length > 0 && (
          <EditableField editMode={editMode} onClick={() => setEditObjArr("awards")}>
            <div><h4 className="text-sm font-medium mb-2">Awards</h4>{data.awards.map((a: any, i: number) => <div key={i} className="flex items-center gap-2 text-sm"><Award className="w-4 h-4 text-yellow-500" />{a.name} {a.year && `(${a.year})`}</div>)}</div>
          </EditableField>
        )}
      </div>
    </Section>
  );
}

function TrustSection({ data, editMode, onUpdate }: { data: any; editMode: boolean; onUpdate: (section: string, data: any) => void }) {
  if (!data) return null;
  const [editField, setEditField] = useState<string | null>(null);
  const [editObjArr, setEditObjArr] = useState<string | null>(null);

  return (
    <Section title="Trust Signals" icon={Shield} editMode={editMode} onEdit={() => setEditField("certifications")}>
      {editField === "certifications" && (
        <EditArrayModal title="Certifications" values={data.certifications || []} onSave={(v) => { onUpdate("trust", { ...data, certifications: v }); setEditField(null); }} onCancel={() => setEditField(null)} />
      )}
      {editField === "partnerships" && (
        <EditArrayModal title="Partnerships" values={data.partnerships || []} onSave={(v) => { onUpdate("trust", { ...data, partnerships: v }); setEditField(null); }} onCancel={() => setEditField(null)} />
      )}
      {editObjArr === "user_stats" && (
        <EditObjectArrayModal title="User Stats" fields={[{ key: "metric", label: "Metric" }, { key: "value", label: "Value" }]} values={data.user_stats || []} onSave={(v) => { onUpdate("trust", { ...data, user_stats: v }); setEditObjArr(null); }} onCancel={() => setEditObjArr(null)} />
      )}
      {editObjArr === "testimonials" && (
        <EditObjectArrayModal title="Testimonials" fields={[{ key: "quote", label: "Quote" }, { key: "source", label: "Source" }]} values={data.testimonials || []} onSave={(v) => { onUpdate("trust", { ...data, testimonials: v }); setEditObjArr(null); }} onCancel={() => setEditObjArr(null)} />
      )}
      <div className="space-y-4">
        {data.certifications?.length > 0 && <EditableField editMode={editMode} onClick={() => setEditField("certifications")}><div><h4 className="text-sm font-medium mb-2">Certifications</h4><div className="flex flex-wrap gap-2">{data.certifications.map((c: string, i: number) => <Tag key={i}>{c}</Tag>)}</div></div></EditableField>}
        {data.partnerships?.length > 0 && <EditableField editMode={editMode} onClick={() => setEditField("partnerships")}><div><h4 className="text-sm font-medium mb-2">Partnerships</h4><div className="flex flex-wrap gap-2">{data.partnerships.map((p: string, i: number) => <Tag key={i}>{p}</Tag>)}</div></div></EditableField>}
        {data.user_stats?.length > 0 && <EditableField editMode={editMode} onClick={() => setEditObjArr("user_stats")}><div className="grid grid-cols-2 sm:grid-cols-3 gap-3">{data.user_stats.map((s: any, i: number) => <div key={i} className="p-3 rounded-xl bg-[var(--muted)] text-center"><div className="text-lg font-bold text-primary-600">{s.value}</div><div className="text-xs text-[var(--muted-foreground)]">{s.metric}</div></div>)}</div></EditableField>}
        {data.testimonials?.length > 0 && <EditableField editMode={editMode} onClick={() => setEditObjArr("testimonials")}><div className="space-y-3">{data.testimonials.map((t: any, i: number) => <blockquote key={i} className="border-l-2 border-primary-600 pl-4 italic text-sm text-[var(--muted-foreground)]">&ldquo;{t.quote}&rdquo; — {t.source}</blockquote>)}</div></EditableField>}
      </div>
    </Section>
  );
}

function ExperienceSection({ data, editMode, onUpdate }: { data: any; editMode: boolean; onUpdate: (section: string, data: any) => void }) {
  if (!data) return null;
  const [editing, setEditing] = useState<string | null>(null);
  const [editObjArr, setEditObjArr] = useState<string | null>(null);

  return (
    <Section title="Experience & FAQ" icon={MessageCircle} editMode={editMode} onEdit={() => setEditing("warranty")}>
      {editing && (
        <EditModal title={editing} value={data[editing] || ""} onSave={(v) => { onUpdate("experience", { ...data, [editing]: v }); setEditing(null); }} onCancel={() => setEditing(null)} />
      )}
      {editObjArr === "faq" && (
        <EditObjectArrayModal title="FAQ" fields={[{ key: "question", label: "Question" }, { key: "answer", label: "Answer" }]} values={data.faq || []} onSave={(v) => { onUpdate("experience", { ...data, faq: v }); setEditObjArr(null); }} onCancel={() => setEditObjArr(null)} />
      )}
      <div className="space-y-4">
        <div className="grid sm:grid-cols-2 gap-4">
          {["warranty", "return_policy", "onboarding", "community"].map((field) => (
            <EditableField key={field} editMode={editMode} onClick={() => setEditing(field)}>
              <KV label={field.replace("_", " ")} value={data[field]} />
            </EditableField>
          ))}
        </div>
        {data.faq?.length > 0 && (
          <EditableField editMode={editMode} onClick={() => setEditObjArr("faq")}>
            <div><h4 className="text-sm font-medium mb-3">FAQ</h4><div className="space-y-3">{data.faq.map((f: any, i: number) => <details key={i} className="group"><summary className="cursor-pointer font-medium text-sm hover:text-primary-600">{f.question}</summary><p className="mt-2 text-sm text-[var(--muted-foreground)] pl-4">{f.answer}</p></details>)}</div></div>
          </EditableField>
        )}
      </div>
    </Section>
  );
}

function AccessSection({ data, editMode, onUpdate }: { data: any; editMode: boolean; onUpdate: (section: string, data: any) => void }) {
  if (!data) return null;
  const [editing, setEditing] = useState<string | null>(null);
  const [editObj, setEditObj] = useState<string | null>(null);
  const [editObjArr, setEditObjArr] = useState<string | null>(null);

  return (
    <Section title="Access & Contact" icon={MapPin} editMode={editMode} onEdit={() => setEditing("official_website")}>
      {editing && (
        <EditModal title={editing} value={data[editing] || ""} onSave={(v) => { onUpdate("access", { ...data, [editing]: v }); setEditing(null); }} onCancel={() => setEditing(null)} />
      )}
      {editObj === "contact" && (
        <EditObjectModal title="Contact" fields={[{ key: "email", label: "Email" }, { key: "phone", label: "Phone" }, { key: "address", label: "Address" }]} values={data.contact || {}} onSave={(v) => { onUpdate("access", { ...data, contact: v }); setEditObj(null); }} onCancel={() => setEditObj(null)} />
      )}
      {editObjArr === "social_media" && (
        <EditObjectArrayModal title="Social Media" fields={[{ key: "platform", label: "Platform" }, { key: "url", label: "URL" }]} values={data.social_media || []} onSave={(v) => { onUpdate("access", { ...data, social_media: v }); setEditObjArr(null); }} onCancel={() => setEditObjArr(null)} />
      )}
      <div className="space-y-4">
        {data.official_website && <EditableField editMode={editMode} onClick={() => setEditing("official_website")}><a href={data.official_website} target="_blank" rel="noopener" className="inline-flex items-center gap-2 text-primary-600 hover:underline"><Globe className="w-4 h-4" />{data.official_website}</a></EditableField>}
        {data.contact && (
          <EditableField editMode={editMode} onClick={() => setEditObj("contact")}>
            <div className="grid sm:grid-cols-2 gap-3">
              {data.contact.email && <div className="flex items-center gap-2 text-sm"><Mail className="w-4 h-4 text-[var(--muted-foreground)]" />{data.contact.email}</div>}
              {data.contact.phone && <div className="flex items-center gap-2 text-sm"><Phone className="w-4 h-4 text-[var(--muted-foreground)]" />{data.contact.phone}</div>}
              {data.contact.address && <div className="flex items-center gap-2 text-sm sm:col-span-2"><MapPin className="w-4 h-4 text-[var(--muted-foreground)]" />{data.contact.address}</div>}
            </div>
          </EditableField>
        )}
        {data.social_media?.length > 0 && <EditableField editMode={editMode} onClick={() => setEditObjArr("social_media")}><div className="flex flex-wrap gap-2">{data.social_media.map((s: any, i: number) => <a key={i} href={s.url} target="_blank" rel="noopener" className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-[var(--muted)] text-sm hover:bg-primary-100 dark:hover:bg-primary-900/30 transition"><ExternalLink className="w-3 h-3" />{s.platform}</a>)}</div></EditableField>}
      </div>
    </Section>
  );
}

function ContentSection({ data, editMode, onUpdate }: { data: any; editMode: boolean; onUpdate: (section: string, data: any) => void }) {
  if (!data) return null;
  const [editObjArr, setEditObjArr] = useState<string | null>(null);
  const news = [...(data.latest_news || []), ...(data.key_announcements || [])];
  if (news.length === 0 && !data.blog_posts?.length && !editMode) return null;

  return (
    <Section title="Content & News" icon={Newspaper} editMode={editMode} onEdit={() => setEditObjArr("latest_news")}>
      {editObjArr === "latest_news" && (
        <EditObjectArrayModal title="Latest News" fields={[{ key: "title", label: "Title" }, { key: "date", label: "Date" }, { key: "summary", label: "Summary" }]} values={data.latest_news || []} onSave={(v) => { onUpdate("content", { ...data, latest_news: v }); setEditObjArr(null); }} onCancel={() => setEditObjArr(null)} />
      )}
      {editObjArr === "key_announcements" && (
        <EditObjectArrayModal title="Key Announcements" fields={[{ key: "title", label: "Title" }, { key: "date", label: "Date" }, { key: "content", label: "Content" }]} values={data.key_announcements || []} onSave={(v) => { onUpdate("content", { ...data, key_announcements: v }); setEditObjArr(null); }} onCancel={() => setEditObjArr(null)} />
      )}
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
        {editMode && (
          <div className="flex gap-2">
            <button onClick={() => setEditObjArr("latest_news")} className="text-xs text-primary-600 hover:underline">Edit News</button>
            <button onClick={() => setEditObjArr("key_announcements")} className="text-xs text-primary-600 hover:underline">Edit Announcements</button>
          </div>
        )}
      </div>
    </Section>
  );
}

function PerceptionSection({ data, editMode, onUpdate }: { data: any; editMode: boolean; onUpdate: (section: string, data: any) => void }) {
  if (!data) return null;
  const [editing, setEditing] = useState<string | null>(null);
  const [editArr, setEditArr] = useState<string | null>(null);
  const [editObj, setEditObj] = useState<string | null>(null);

  return (
    <Section title="Perception" icon={Eye} editMode={editMode} onEdit={() => setEditArr("personality_traits")}>
      {editing && <EditModal title={editing} value={data[editing] || ""} onSave={(v) => { onUpdate("perception", { ...data, [editing]: v }); setEditing(null); }} onCancel={() => setEditing(null)} />}
      {editArr === "personality_traits" && <EditArrayModal title="Personality Traits" values={data.personality_traits || []} onSave={(v) => { onUpdate("perception", { ...data, personality_traits: v }); setEditArr(null); }} onCancel={() => setEditArr(null)} />}
      {editArr === "usage_occasions" && <EditArrayModal title="Usage Occasions" values={data.usage_occasions || []} onSave={(v) => { onUpdate("perception", { ...data, usage_occasions: v }); setEditArr(null); }} onCancel={() => setEditArr(null)} />}
      {editObj === "primary_audience" && <EditObjectModal title="Primary Audience" fields={[{ key: "demographics", label: "Demographics" }, { key: "psychographics", label: "Psychographics" }, { key: "lifestyle", label: "Lifestyle" }]} values={data.primary_audience || {}} onSave={(v) => { onUpdate("perception", { ...data, primary_audience: v }); setEditObj(null); }} onCancel={() => setEditObj(null)} />}
      <div className="space-y-4">
        {data.personality_traits?.length > 0 && <EditableField editMode={editMode} onClick={() => setEditArr("personality_traits")}><div className="flex flex-wrap gap-2">{data.personality_traits.map((t: string, i: number) => <Tag key={i}>{t}</Tag>)}</div></EditableField>}
        <div className="grid sm:grid-cols-2 gap-4">
          {["brand_tone", "price_positioning", "price_benchmark", "category_association"].map((field) => (
            <EditableField key={field} editMode={editMode} onClick={() => setEditing(field)}>
              <KV label={field.replace(/_/g, " ")} value={data[field]} />
            </EditableField>
          ))}
        </div>
        {data.primary_audience && (
          <EditableField editMode={editMode} onClick={() => setEditObj("primary_audience")}>
            <div className="p-4 rounded-xl bg-[var(--muted)]">
              <h4 className="text-sm font-medium mb-2 flex items-center gap-1"><Users className="w-4 h-4" /> Primary Audience</h4>
              <div className="text-sm space-y-1">
                {data.primary_audience.demographics && <p><strong>Demographics:</strong> {data.primary_audience.demographics}</p>}
                {data.primary_audience.psychographics && <p><strong>Psychographics:</strong> {data.primary_audience.psychographics}</p>}
                {data.primary_audience.lifestyle && <p><strong>Lifestyle:</strong> {data.primary_audience.lifestyle}</p>}
              </div>
            </div>
          </EditableField>
        )}
        {data.usage_occasions?.length > 0 && <EditableField editMode={editMode} onClick={() => setEditArr("usage_occasions")}><div><h4 className="text-sm font-medium mb-2">Usage Occasions</h4><div className="flex flex-wrap gap-2">{data.usage_occasions.map((o: string, i: number) => <Tag key={i}>{o}</Tag>)}</div></div></EditableField>}
      </div>
    </Section>
  );
}

function DecisionSection({ data, editMode, onUpdate }: { data: any; editMode: boolean; onUpdate: (section: string, data: any) => void }) {
  if (!data) return null;
  const [editing, setEditing] = useState<string | null>(null);
  const [editObjArr, setEditObjArr] = useState<string | null>(null);

  return (
    <Section title="Decision Factors" icon={BarChart3} editMode={editMode} onEdit={() => setEditObjArr("category_key_factors")}>
      {editing && <EditModal title={editing} value={data[editing] || ""} onSave={(v) => { onUpdate("decision_factors", { ...data, [editing]: v }); setEditing(null); }} onCancel={() => setEditing(null)} />}
      {editObjArr === "category_key_factors" && (
        <EditObjectArrayModal title="Key Factors" fields={[{ key: "factor", label: "Factor" }, { key: "brand_score", label: "Score" }, { key: "evidence", label: "Evidence" }]} values={data.category_key_factors || []} onSave={(v) => { onUpdate("decision_factors", { ...data, category_key_factors: v }); setEditObjArr(null); }} onCancel={() => setEditObjArr(null)} />
      )}
      {editObjArr === "perceived_risks" && (
        <EditObjectArrayModal title="Perceived Risks" fields={[{ key: "risk", label: "Risk" }, { key: "mitigation", label: "Mitigation" }]} values={data.perceived_risks || []} onSave={(v) => { onUpdate("decision_factors", { ...data, perceived_risks: v }); setEditObjArr(null); }} onCancel={() => setEditObjArr(null)} />
      )}
      <div className="space-y-4">
        {data.category_key_factors?.length > 0 && (
          <EditableField editMode={editMode} onClick={() => setEditObjArr("category_key_factors")}>
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
          </EditableField>
        )}
        {data.perceived_risks?.length > 0 && (
          <EditableField editMode={editMode} onClick={() => setEditObjArr("perceived_risks")}>
            <div><h4 className="text-sm font-medium mb-2">Perceived Risks</h4>{data.perceived_risks.map((r: any, i: number) => <div key={i} className="mb-2"><p className="text-sm font-medium text-red-500">⚠ {r.risk}</p>{r.mitigation && <p className="text-xs text-[var(--muted-foreground)] ml-4">→ {r.mitigation}</p>}</div>)}</div>
          </EditableField>
        )}
        <div className="grid sm:grid-cols-2 gap-4">
          {["switching_cost", "trial_barrier"].map((field) => (
            <EditableField key={field} editMode={editMode} onClick={() => setEditing(field)}>
              <KV label={field.replace("_", " ")} value={data[field]} />
            </EditableField>
          ))}
        </div>
      </div>
    </Section>
  );
}

function VitalitySection({ data, editMode, onUpdate }: { data: any; editMode: boolean; onUpdate: (section: string, data: any) => void }) {
  if (!data) return null;
  const [editing, setEditing] = useState<string | null>(null);
  const fields = ["content_frequency", "last_product_launch", "last_campaign", "growth_signal", "community_size", "nps_or_satisfaction", "market_position", "industry_role"];

  return (
    <Section title="Vitality" icon={Activity} editMode={editMode} onEdit={() => setEditing(fields[0])}>
      {editing && <EditModal title={editing.replace(/_/g, " ")} value={data[editing] || ""} onSave={(v) => { onUpdate("vitality", { ...data, [editing]: v }); setEditing(null); }} onCancel={() => setEditing(null)} />}
      <div className="grid sm:grid-cols-2 gap-4">
        {fields.map((field) => (
          <EditableField key={field} editMode={editMode} onClick={() => setEditing(field)}>
            <KV label={field.replace(/_/g, " ")} value={data[field]} />
          </EditableField>
        ))}
      </div>
    </Section>
  );
}

export default function BrandDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [brand, setBrand] = useState<Brand | null>(null);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [saving, setSaving] = useState(false);

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

  const handleUpdate = async (section: string, data: any) => {
    setSaving(true);
    try {
      const updated = await updateKnowledge(id, { [section]: data });
      setBrand((prev) => prev ? { ...prev, data: updated } : prev);
    } catch (e) {
      console.error("Update failed", e);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div>;
  if (!brand) return <div className="text-center py-20">Brand not found</div>;

  const isGenerating = brand.status === "pending" || brand.status === "processing";
  const d = brand.data;

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <Link href="/brands" className="inline-flex items-center gap-1 text-sm text-[var(--muted-foreground)] hover:text-primary-600">
          <ArrowLeft className="w-4 h-4" /> Back to brands
        </Link>
        <div className="flex items-center gap-3">
          {d && (
            <>
              <Link
                href={`/kb/${id}`}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-[var(--muted)] hover:bg-primary-100 dark:hover:bg-primary-900/30 transition"
              >
                <Globe className="w-3.5 h-3.5" /> Public Page
              </Link>
              <button
                onClick={() => setEditMode(!editMode)}
                className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition ${
                  editMode
                    ? "bg-primary-600 text-white"
                    : "bg-[var(--muted)] hover:bg-primary-100 dark:hover:bg-primary-900/30"
                }`}
              >
                {editMode ? <><Check className="w-3.5 h-3.5" /> Editing</> : <><Pencil className="w-3.5 h-3.5" /> Edit</>}
              </button>
            </>
          )}
          {saving && <Loader2 className="w-4 h-4 animate-spin text-primary-600" />}
        </div>
      </div>

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
          <KBSearchBar brandId={id} />
          <IdentityCard data={d.identity} editMode={editMode} onUpdate={handleUpdate} />
          <OfferingsGrid data={d.offerings} editMode={editMode} onUpdate={handleUpdate} />
          <DifferentiationSection data={d.differentiation} editMode={editMode} onUpdate={handleUpdate} />
          <TrustSection data={d.trust} editMode={editMode} onUpdate={handleUpdate} />
          <ExperienceSection data={d.experience} editMode={editMode} onUpdate={handleUpdate} />
          <AccessSection data={d.access} editMode={editMode} onUpdate={handleUpdate} />
          <ContentSection data={d.content} editMode={editMode} onUpdate={handleUpdate} />
          <PerceptionSection data={d.perception} editMode={editMode} onUpdate={handleUpdate} />
          <DecisionSection data={d.decision_factors} editMode={editMode} onUpdate={handleUpdate} />
          <VitalitySection data={d.vitality} editMode={editMode} onUpdate={handleUpdate} />
          <IntegrationPanel brandId={id} />
        </div>
      )}

      {/* Chat panel */}
      {d && <ChatPanel brandId={id} />}
    </div>
  );
}
