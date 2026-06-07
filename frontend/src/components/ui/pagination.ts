export const paginationPageSizeOptions = [10, 25, 50] as const;

export type PaginationPageSize = (typeof paginationPageSizeOptions)[number];

export type PaginationRange = {
  currentPageIndex: number;
  endIndex: number;
  pageCount: number;
  startIndex: number;
};

export function getPaginationRange(
  totalCount: number,
  pageSize: PaginationPageSize,
  pageIndex: number,
): PaginationRange {
  const pageCount = Math.max(1, Math.ceil(totalCount / pageSize));
  const currentPageIndex = Math.min(Math.max(0, pageIndex), pageCount - 1);
  const startIndex = totalCount === 0 ? 0 : currentPageIndex * pageSize;
  const endIndex =
    totalCount === 0 ? 0 : Math.min(startIndex + pageSize, totalCount);

  return { currentPageIndex, endIndex, pageCount, startIndex };
}

export function paginateItems<T>(
  items: T[],
  pageSize: PaginationPageSize,
  pageIndex: number,
) {
  const range = getPaginationRange(items.length, pageSize, pageIndex);
  return {
    ...range,
    items: items.slice(range.startIndex, range.endIndex),
  };
}
