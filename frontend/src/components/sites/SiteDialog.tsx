import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogCloseButton, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

interface SiteDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    name: string;
    description: string | null;
    tz: string;
    geo_point: null;
  }) => Promise<void>;
}

export function SiteDialog({ open, onClose, onSubmit }: SiteDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tz, setTz] = useState("UTC");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setName("");
      setDescription("");
      setTz("UTC");
      setIsSubmitting(false);
      setSubmitError(null);
    }
  }, [open]);

  async function handleSubmit() {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await onSubmit({
        name,
        description: description || null,
        tz,
        geo_point: null,
      });
    } catch {
      setSubmitError("Unable to save site. Check the values and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      title="Create site"
      description="Add a deployment location to the Vezor fleet and attach its operating time zone."
    >
      <div className="grid gap-4">
        <label className="grid gap-2 text-sm text-[#d8e2f2]">
          <span>Site name</span>
          <Input
            aria-label="Site name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="HQ"
          />
        </label>
        <label className="grid gap-2 text-sm text-[#d8e2f2]">
          <span>Description</span>
          <Input
            aria-label="Description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Main campus or operating zone"
          />
        </label>
        <label className="grid gap-2 text-sm text-[#d8e2f2]">
          <span>Time zone</span>
          <Input
            aria-label="Time zone"
            value={tz}
            onChange={(event) => setTz(event.target.value)}
            placeholder="Europe/Zurich"
          />
        </label>
      </div>
      {submitError ? (
        <p className="mt-4 text-sm font-medium text-[#ff9ca6]">{submitError}</p>
      ) : null}
      <DialogFooter>
        <DialogCloseButton onClick={onClose}>Cancel</DialogCloseButton>
        <Button onClick={() => void handleSubmit()} disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : "Save site"}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
