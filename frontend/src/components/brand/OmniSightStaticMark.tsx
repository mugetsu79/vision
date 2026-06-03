import { productBrand } from "@/brand/product";

export function OmniSightStaticMark({ className = "" }: { className?: string }) {
  return (
    <img
      src={productBrand.runtimeAssets.logo2d}
      alt={`${productBrand.name} mark`}
      className={className}
      draggable={false}
    />
  );
}
