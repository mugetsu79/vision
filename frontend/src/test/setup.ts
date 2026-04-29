import "@testing-library/jest-dom/vitest";

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();

  return {
    get length() {
      return values.size;
    },
    clear() {
      values.clear();
    },
    getItem(key: string) {
      return values.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(values.keys())[index] ?? null;
    },
    removeItem(key: string) {
      values.delete(key);
    },
    setItem(key: string, value: string) {
      values.set(key, value);
    },
  };
}

const testLocalStorage = createMemoryStorage();

Object.defineProperty(window, "localStorage", {
  configurable: true,
  value: testLocalStorage,
});
Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: testLocalStorage,
});

function createCompatibleRequest(nativeRequest: typeof Request): typeof Request {
  const compatibleRequest = function (
    input: RequestInfo | URL,
    init?: RequestInit,
  ) {
    try {
      return new nativeRequest(input, init);
    } catch (error) {
      if (error instanceof TypeError && init?.signal) {
        const initWithoutSignal = { ...init };
        delete initWithoutSignal.signal;
        return new nativeRequest(input, initWithoutSignal);
      }
      throw error;
    }
  } as unknown as typeof Request;

  Object.setPrototypeOf(compatibleRequest, nativeRequest);
  compatibleRequest.prototype = nativeRequest.prototype;
  return compatibleRequest;
}

if (typeof Request !== "undefined") {
  const compatibleRequest = createCompatibleRequest(Request);
  Object.defineProperty(globalThis, "Request", {
    configurable: true,
    value: compatibleRequest,
  });
  Object.defineProperty(window, "Request", {
    configurable: true,
    value: compatibleRequest,
  });
}
