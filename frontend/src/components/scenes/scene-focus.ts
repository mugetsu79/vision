export interface SceneFocusItem {
  id: string;
  name: string;
  siteId?: string | null;
  siteName?: string | null;
}

export function filterSceneFocusItems(
  items: SceneFocusItem[],
  searchValue: string,
): SceneFocusItem[] {
  const query = searchValue.trim().toLowerCase();
  if (!query) {
    return items;
  }
  const tokens = query.split(/\s+/);

  return items.filter((item) => {
    const siteName = item.siteName ?? "";
    const haystack = `${item.name} ${siteName}`.toLowerCase();
    return tokens.every((token) => haystack.includes(token));
  });
}
