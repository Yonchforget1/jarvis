import { Loader2 } from "lucide-react";

export default function AppLoading() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="flex flex-col items-center gap-3 animate-fade-in-up">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <span className="text-sm text-muted-foreground/60">Loading...</span>
      </div>
    </div>
  );
}
