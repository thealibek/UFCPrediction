"use client";

import { Check, Crown, Sparkles } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useUser } from "@/lib/user";

const features = [
  "Win probability for every fight",
  "Predicted method (KO / Sub / Decision) + round",
  "Full AI reasoning per fight",
  "Historical accuracy & calibration insights",
  "Email alerts before each event",
];

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function UpgradeModal({ open, onOpenChange }: Props) {
  const { setSubscribed, setRole } = useUser();

  const handleCheckout = () => {
    // Stripe stub — в проде: fetch('/api/checkout', ...).then(redirect)
    setRole("paid");
    setSubscribed(true);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="grid place-items-center h-12 w-12 rounded-xl bg-primary text-primary-foreground mb-2">
            <Crown className="h-5 w-5" />
          </div>
          <DialogTitle className="text-xl">Upgrade to Octagon Pro</DialogTitle>
          <DialogDescription>
            Unlock full AI predictions, calibrated probability, and history dashboard.
          </DialogDescription>
        </DialogHeader>

        <div className="my-2 rounded-lg border bg-muted/30 p-4">
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-semibold tracking-tight">$19</span>
            <span className="text-sm text-muted-foreground">/month</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">Cancel anytime · 7-day money back</p>
        </div>

        <ul className="space-y-2.5">
          {features.map((f) => (
            <li key={f} className="flex items-start gap-2 text-sm">
              <Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
              <span>{f}</span>
            </li>
          ))}
        </ul>

        <DialogFooter className="mt-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Not now
          </Button>
          <Button onClick={handleCheckout} className="gap-1.5">
            <Sparkles className="h-3.5 w-3.5" />
            Continue to checkout
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
