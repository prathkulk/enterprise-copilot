import { redirect } from "next/navigation";

export default async function CollectionIndexPage({
  params,
}: {
  params: Promise<{ collectionId: string }>;
}) {
  const { collectionId } = await params;
  redirect(`/collections/${collectionId}/documents`);
}
