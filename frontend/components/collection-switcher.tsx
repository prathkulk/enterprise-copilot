"use client";

import { useRouter } from "next/navigation";
import type { Collection } from "@/lib/types";

interface CollectionSwitcherProps {
  collections: Collection[];
  selectedCollectionId: number | null;
  routeBuilder: (collectionId: number) => string;
}

export function CollectionSwitcher({
  collections,
  selectedCollectionId,
  routeBuilder,
}: CollectionSwitcherProps) {
  const router = useRouter();

  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-[var(--muted)]">
        Collection selector
      </span>
      <select
        value={selectedCollectionId ?? ""}
        onChange={(event) => {
          const nextCollectionId = Number(event.target.value);
          if (!Number.isNaN(nextCollectionId)) {
            router.push(routeBuilder(nextCollectionId));
          }
        }}
        className="field"
      >
        {collections.map((collection) => (
          <option key={collection.id} value={collection.id}>
            {collection.name}
          </option>
        ))}
      </select>
    </label>
  );
}
