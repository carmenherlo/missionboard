// Search as in WhatsApp: every word typed must be the start of a word in
// the item's name or keywords. Case and accents are ignored.

export function normalize(text) {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export function words(text) {
  return normalize(text).split(/[^a-z0-9]+/).filter(Boolean);
}

// items: [{ words, nameWords, featured }]. Order: featured items first, then
// matches in the name before matches only in the keywords.
export function search(items, query, limit = Infinity) {
  const terms = words(query);
  if (!terms.length) return [];
  const hits = [];
  for (const item of items) {
    if (!terms.every((t) => item.words.some((w) => w.startsWith(t)))) continue;
    const inName = terms.every((t) => item.nameWords.some((w) => w.startsWith(t)));
    hits.push([(item.featured ? 0 : 2) + (inName ? 0 : 1), item]);
  }
  hits.sort((a, b) => a[0] - b[0]);
  return hits.slice(0, limit).map(([, item]) => item);
}
