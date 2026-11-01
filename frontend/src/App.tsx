import { FormEvent, useEffect, useMemo, useState } from "react";

type SearchSummary = {
  id: number;
  name: string | null;
  url: string;
  site: string;
  status: string;
  progress_done: number;
  progress_total: number;
  price_sort_order: "asc" | "desc";
  warning?: string | null;
  error?: string | null;
};

type Research = {
  low: number | null;
  high: number | null;
  median: number | null;
  confidence: number;
  sample_size: number;
  query_text: string;
  warning?: string | null;
  comparables: Comparable[];
};

type Comparable = {
  id: number;
  source: string;
  title: string;
  price: number;
  currency: string;
  url: string;
};

type Lot = {
  id: number;
  lot_number: string | null;
  title: string;
  current_bid: number | null;
  opening_bid: number | null;
  lot_url: string | null;
  latest_research: Research | null;
};

type SearchDetail = SearchSummary & {
  min_price: number | null;
  max_price: number | null;
  max_items: number;
  keywords: string | null;
  lots: Lot[];
};

type SortField = "lot" | "title" | "bid" | "quick_bid" | "low" | "high" | "median" | "confidence" | "margin";
type SortDirection = "asc" | "desc";

const API_BASE = "http://localhost:8000";

export function App() {
  const [searchName, setSearchName] = useState("");
  const [url, setUrl] = useState("https://www.liveauctioneers.com/");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [maxItems, setMaxItems] = useState(20);
  const [priceSortOrder, setPriceSortOrder] = useState<"asc" | "desc">("asc");
  const [keywords, setKeywords] = useState("");
  const [searchId, setSearchId] = useState<number | null>(null);
  const [search, setSearch] = useState<SearchDetail | null>(null);
  const [history, setHistory] = useState<SearchSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sortField, setSortField] = useState<SortField>("margin");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  async function loadHistory() {
    const res = await fetch(`${API_BASE}/api/searches`);
    if (!res.ok) {
      return;
    }
    const rows = (await res.json()) as SearchSummary[];
    setHistory(rows);
  }

  async function loadSearch(id: number, syncForm: boolean = false) {
    const res = await fetch(`${API_BASE}/api/searches/${id}`);
    if (!res.ok) {
      throw new Error(await res.text());
    }
    const body = (await res.json()) as SearchDetail;
    setSearch(body);
    if (syncForm) {
      setSearchName(body.name ?? "");
      setUrl(body.url);
      setMinPrice(body.min_price !== null ? String(body.min_price) : "");
      setMaxPrice(body.max_price !== null ? String(body.max_price) : "");
      setMaxItems(body.max_items);
      setPriceSortOrder(body.price_sort_order);
      setKeywords(body.keywords ?? "");
    }
  }

  useEffect(() => {
    loadHistory().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!searchId) {
      return;
    }
    const currentSearchId = searchId;
    const source = new EventSource(`${API_BASE}/api/events/${currentSearchId}`);
    const refresh = () => {
      loadSearch(currentSearchId).catch(() => undefined);
      loadHistory().catch(() => undefined);
    };

    source.onmessage = refresh;
    source.addEventListener("progress", refresh);
    source.addEventListener("lot_researched", refresh);
    source.addEventListener("done", () => {
      refresh();
      source.close();
    });
    source.addEventListener("error", () => {
      refresh();
      source.close();
    });
    source.onerror = () => {
      refresh();
      source.close();
    };
    return () => source.close();
  }, [searchId]);

  const sortedLots = useMemo(() => {
    if (!search) {
      return [];
    }
    const getSortValue = (lot: Lot): string | number => {
      switch (sortField) {
        case "lot": {
          const raw = lot.lot_number ?? "";
          const n = Number.parseInt(raw.replace(/\D+/g, ""), 10);
          return Number.isNaN(n) ? raw.toLowerCase() : n;
        }
        case "title":
          return lot.title.toLowerCase();
        case "bid":
          return lot.current_bid ?? -1;
        case "quick_bid":
          return lot.opening_bid ?? -1;
        case "low":
          return lot.latest_research?.low ?? -1;
        case "high":
          return lot.latest_research?.high ?? -1;
        case "median":
          return lot.latest_research?.median ?? -1;
        case "confidence":
          return lot.latest_research?.confidence ?? -1;
        case "margin":
        default:
          return (lot.latest_research?.median ?? -1) - (lot.current_bid ?? 0);
      }
    };

    return [...search.lots].sort((a, b) => {
      const aValue = getSortValue(a);
      const bValue = getSortValue(b);

      if (typeof aValue === "string" && typeof bValue === "string") {
        const cmp = aValue.localeCompare(bValue);
        return sortDirection === "asc" ? cmp : -cmp;
      }
      const cmp = Number(aValue) - Number(bValue);
      return sortDirection === "asc" ? cmp : -cmp;
    });
  }, [search, sortDirection, sortField]);

  function onSort(field: SortField) {
    if (field === sortField) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
      return;
    }
    setSortField(field);
    setSortDirection("asc");
  }

  function sortLabel(field: SortField, label: string) {
    if (sortField !== field) {
      return label;
    }
    return `${label} ${sortDirection === "asc" ? "↑" : "↓"}`;
  }

  function canDeleteSearch(status: string) {
    return !["queued", "fetching", "researching"].includes(status);
  }

  const isSearchInProgress = search ? ["queued", "fetching", "researching"].includes(search.status) : false;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/searches`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: searchName.trim() || null,
          url,
          min_price: minPrice ? Number(minPrice) : null,
          max_price: maxPrice ? Number(maxPrice) : null,
          max_items: maxItems,
          price_sort_order: priceSortOrder,
          keywords: keywords || null,
        }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const body = (await res.json()) as { search_id: number };
      setSearchId(body.search_id);
      await loadSearch(body.search_id, true);
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function deleteSearch(id: number) {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/searches/${id}`, { method: "DELETE" });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      if (searchId === id) {
        setSearchId(null);
        setSearch(null);
      }
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  function findComparableForValue(lot: Lot, value: number | null, mode: "min" | "max" | "closest"): Comparable | null {
    if (value === null) {
      return null;
    }
    const comparables = lot.latest_research?.comparables ?? [];
    if (comparables.length === 0) {
      return null;
    }
    if (mode === "min") {
      return comparables.reduce((best, cur) => (cur.price < best.price ? cur : best));
    }
    if (mode === "max") {
      return comparables.reduce((best, cur) => (cur.price > best.price ? cur : best));
    }
    return comparables.reduce((best, cur) =>
      Math.abs(cur.price - value) < Math.abs(best.price - value) ? cur : best
    );
  }

  function renderMetricCell(lot: Lot, value: number | null, mode: "min" | "max" | "closest") {
    if (value === null) {
      return "—";
    }
    const comparable = findComparableForValue(lot, value, mode);
    if (!comparable?.url) {
      return value;
    }
    return (
      <a href={comparable.url} target="_blank" rel="noreferrer" title={`${comparable.source}: ${comparable.title}`}>
        {value}
      </a>
    );
  }

  return (
    <div className="page">
      <h1>Auction Scout</h1>
      <form onSubmit={submit} className="search-form">
        <input className="url-input" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Auction URL" required />
        <div className="criteria-row">
          <input value={searchName} onChange={(e) => setSearchName(e.target.value)} placeholder="Search name (optional)" />
          <input value={minPrice} onChange={(e) => setMinPrice(e.target.value)} placeholder="Min price" />
          <input value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} placeholder="Max price" />
          <input
            type="number"
            min={1}
            max={200}
            value={maxItems}
            onChange={(e) => setMaxItems(Number(e.target.value))}
            placeholder="Max lots"
          />
          <select value={priceSortOrder} onChange={(e) => setPriceSortOrder(e.target.value as "asc" | "desc")}>
            <option value="asc">Price: low to high</option>
            <option value="desc">Price: high to low</option>
          </select>
          <input value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="Keywords (comma-separated)" />
          <button type="submit" disabled={isSubmitting}>{isSubmitting ? "Searching..." : "Search"}</button>
        </div>
      </form>
      {error && <p className="error">{error}</p>}
      {search && (
        <section>
          <h2>
            {search.name ? `${search.name} · ` : ""}
            Search #{search.id} · {search.site} · {search.status} ({search.progress_done}/{search.progress_total})
          </h2>
          <p className="filters-summary">
            Filters used: min {search.min_price ?? "—"} · max {search.max_price ?? "—"} · max results {search.max_items}
            {" · "}price order {search.price_sort_order} · keywords {search.keywords || "—"}
          </p>
          {isSearchInProgress && (
            <div className="progress-indicator" role="status" aria-live="polite">
              <span className="progress-spinner" aria-hidden="true"></span>
              <span>Search in progress…</span>
            </div>
          )}
          {search.warning && <p className="warn">{search.warning}</p>}
          {search.error && <p className="error">{search.error}</p>}
          <table>
            <thead>
              <tr>
                <th><button type="button" className="sort-btn" onClick={() => onSort("lot")}>{sortLabel("lot", "Lot")}</button></th>
                <th><button type="button" className="sort-btn" onClick={() => onSort("title")}>{sortLabel("title", "Title")}</button></th>
                <th><button type="button" className="sort-btn" onClick={() => onSort("bid")}>{sortLabel("bid", "Bid (CAD)")}</button></th>
                <th><button type="button" className="sort-btn" onClick={() => onSort("quick_bid")}>{sortLabel("quick_bid", "Quick Bid (CAD)")}</button></th>
                <th><button type="button" className="sort-btn" onClick={() => onSort("low")}>{sortLabel("low", "Market low")}</button></th>
                <th><button type="button" className="sort-btn" onClick={() => onSort("high")}>{sortLabel("high", "Market high")}</button></th>
                <th><button type="button" className="sort-btn" onClick={() => onSort("median")}>{sortLabel("median", "Median")}</button></th>
                <th><button type="button" className="sort-btn" onClick={() => onSort("confidence")}>{sortLabel("confidence", "Confidence")}</button></th>
              </tr>
            </thead>
            <tbody>
              {sortedLots.map((lot) => (
                <tr key={lot.id}>
                  <td>{lot.lot_number ?? "—"}</td>
                  <td>
                    {lot.lot_url ? (
                      <a href={lot.lot_url} target="_blank" rel="noreferrer">
                        {lot.title}
                      </a>
                    ) : (
                      lot.title
                    )}
                  </td>
                  <td>{lot.current_bid ?? "—"}</td>
                  <td>{lot.opening_bid ?? "—"}</td>
                  <td>{renderMetricCell(lot, lot.latest_research?.low ?? null, "min")}</td>
                  <td>{renderMetricCell(lot, lot.latest_research?.high ?? null, "max")}</td>
                  <td>{renderMetricCell(lot, lot.latest_research?.median ?? null, "closest")}</td>
                  <td>
                    {lot.latest_research ? `${Math.round(lot.latest_research.confidence * 100)}%` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <section>
        <h2>Recent searches</h2>
        <ul>
          {history.map((s) => (
            <li key={s.id}>
              <div className="history-row">
                <button onClick={() => { setSearchId(s.id); loadSearch(s.id, true).catch(() => undefined); }}>
                  {s.name ? `${s.name} · ` : ""}#{s.id} {s.site} {s.status} ({s.price_sort_order})
                </button>
                <button
                  type="button"
                  className="danger-btn"
                  disabled={!canDeleteSearch(s.status)}
                  title={canDeleteSearch(s.status) ? "Delete search" : "Search is still running"}
                  onClick={() => { deleteSearch(s.id).catch(() => undefined); }}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
