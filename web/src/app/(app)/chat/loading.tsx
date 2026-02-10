import { Skeleton } from "@/components/ui/skeleton";

export default function ChatLoading() {
  return (
    <div className="flex h-full flex-col">
      {/* Header skeleton */}
      <div className="flex items-center gap-3 border-b border-border/50 px-4 py-3">
        <Skeleton className="h-5 w-32 rounded-lg" />
        <Skeleton className="ml-auto h-5 w-20 rounded-lg" />
      </div>
      {/* Messages skeleton */}
      <div className="flex-1 p-4 space-y-4">
        <div className="flex items-start gap-3">
          <Skeleton className="h-8 w-8 rounded-full shrink-0" />
          <div className="space-y-2 flex-1 max-w-md">
            <Skeleton className="h-4 w-full rounded" />
            <Skeleton className="h-4 w-3/4 rounded" />
          </div>
        </div>
        <div className="flex items-start gap-3 justify-end">
          <div className="space-y-2 flex-1 max-w-sm">
            <Skeleton className="h-4 w-full rounded" />
            <Skeleton className="h-4 w-1/2 rounded" />
          </div>
          <Skeleton className="h-8 w-8 rounded-full shrink-0" />
        </div>
        <div className="flex items-start gap-3">
          <Skeleton className="h-8 w-8 rounded-full shrink-0" />
          <div className="space-y-2 flex-1 max-w-lg">
            <Skeleton className="h-4 w-full rounded" />
            <Skeleton className="h-4 w-5/6 rounded" />
            <Skeleton className="h-4 w-2/3 rounded" />
          </div>
        </div>
      </div>
      {/* Input skeleton */}
      <div className="border-t border-border/50 p-4">
        <Skeleton className="h-12 w-full rounded-xl" />
      </div>
    </div>
  );
}
