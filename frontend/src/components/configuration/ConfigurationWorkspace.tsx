import { useMemo, useState } from "react";
import {
  Brain,
  Cpu,
  Database,
  Radio,
  ShieldCheck,
  Workflow,
} from "lucide-react";

import { EffectiveConfigurationPanel } from "@/components/configuration/EffectiveConfigurationPanel";
import { ProfileBindingPanel } from "@/components/configuration/ProfileBindingPanel";
import { ProfileEditor } from "@/components/configuration/ProfileEditor";
import { ProfileImpactDialog } from "@/components/configuration/ProfileImpactDialog";
import { ProfileInventory } from "@/components/configuration/ProfileInventory";
import {
  CONFIGURATION_KINDS,
  labelForKind,
} from "@/components/configuration/configuration-copy";
import {
  useConfigurationBindings,
  useConfigurationCatalog,
  useConfigurationProfileImpact,
  useConfigurationProfiles,
  useCreateConfigurationProfile,
  useDeleteConfigurationBinding,
  useDeleteConfigurationProfile,
  useTestConfigurationProfile,
  useUpdateConfigurationProfile,
  useUpsertConfigurationBinding,
  type OperatorConfigKind,
  type OperatorConfigProfile,
  type OperatorConfigProfileCreate,
} from "@/hooks/use-configuration";
import { Button } from "@/components/ui/button";
import { WorkspaceSurface, StatusToneBadge } from "@/components/layout/workspace-surfaces";

type NamedTarget = {
  id: string;
  name?: string;
  hostname?: string | null;
};

type ConfigurationWorkspaceProps = {
  cameras?: NamedTarget[];
  sites?: NamedTarget[];
  edgeNodes?: NamedTarget[];
};

type ConfigurationFeedback = {
  tone: "healthy" | "danger" | "accent" | "muted";
  message: string;
};

const KIND_ICONS: Record<OperatorConfigKind, typeof Database> = {
  evidence_storage: Database,
  stream_delivery: Radio,
  runtime_selection: Cpu,
  privacy_policy: ShieldCheck,
  llm_provider: Brain,
  operations_mode: Workflow,
};

function createProfileDraft(
  kind: OperatorConfigKind,
  profiles: OperatorConfigProfile[],
  source?: OperatorConfigProfile | null,
): OperatorConfigProfile {
  const baseName = source ? `${source.name} copy` : `New ${labelForKind(kind)} profile`;
  const baseSlug = source
    ? slugify(`${source.slug}-copy`)
    : slugify(`new-${kind.replaceAll("_", "-")}`);
  const slug = uniqueSlug(baseSlug, profiles.map((profile) => profile.slug));

  return {
    id: `draft-${kind}`,
    tenant_id: source?.tenant_id ?? "draft",
    kind,
    scope: source?.scope ?? "tenant",
    name: baseName,
    slug,
    enabled: source?.enabled ?? true,
    is_default: false,
    config: source?.config ?? {},
    secret_state: {},
    validation_status: "unvalidated",
    validation_message: null,
    validated_at: null,
    config_hash: "0".repeat(64),
    created_at: source?.created_at ?? "1970-01-01T00:00:00Z",
    updated_at: source?.updated_at ?? "1970-01-01T00:00:00Z",
  };
}

function uniqueSlug(baseSlug: string, existingSlugs: string[]) {
  const existing = new Set(existingSlugs);
  let candidate = baseSlug || "profile";
  let index = 2;
  while (existing.has(candidate)) {
    candidate = `${baseSlug}-${index}`;
    index += 1;
  }
  return candidate;
}

function slugify(value: string) {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "profile";
}

export function ConfigurationWorkspace({
  cameras = [],
  sites = [],
  edgeNodes = [],
}: ConfigurationWorkspaceProps) {
  const catalog = useConfigurationCatalog();
  const [activeKind, setActiveKind] = useState<OperatorConfigKind>("evidence_storage");
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [draftProfile, setDraftProfile] = useState<OperatorConfigProfile | null>(null);
  const [pendingDeleteProfile, setPendingDeleteProfile] =
    useState<OperatorConfigProfile | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [profileFeedback, setProfileFeedback] = useState<ConfigurationFeedback | null>(null);
  const [bindingFeedback, setBindingFeedback] = useState<ConfigurationFeedback | null>(null);
  const profilesQuery = useConfigurationProfiles(activeKind);
  const bindingsQuery = useConfigurationBindings(activeKind);
  const profileImpactQuery = useConfigurationProfileImpact(pendingDeleteProfile?.id);
  const createProfile = useCreateConfigurationProfile();
  const updateProfile = useUpdateConfigurationProfile();
  const deleteProfile = useDeleteConfigurationProfile();
  const deleteBinding = useDeleteConfigurationBinding();
  const testProfile = useTestConfigurationProfile();
  const upsertBinding = useUpsertConfigurationBinding();

  const profiles = useMemo(
    () => (profilesQuery.data ?? []).filter((profile) => profile.kind === activeKind),
    [activeKind, profilesQuery.data],
  );
  const selectedProfile =
    profiles.find((profile) => profile.id === selectedProfileId) ?? profiles[0] ?? null;
  const editorDraftProfile = isCreating ? draftProfile : null;
  const catalogLabels = new Map(
    (catalog.data?.kinds ?? []).map((item) => [item.kind, item.label]),
  );
  const bindings = useMemo(() => bindingsQuery.data ?? [], [bindingsQuery.data]);
  const bindingCountByProfileId = useMemo(() => {
    const counts = new Map<string, number>();
    for (const binding of bindings) {
      counts.set(binding.profile_id, (counts.get(binding.profile_id) ?? 0) + 1);
    }
    return counts;
  }, [bindings]);

  async function handleSave(payload: OperatorConfigProfileCreate) {
    setProfileFeedback(null);
    try {
      if (selectedProfile && !isCreating) {
        await updateProfile.mutateAsync({
          profileId: selectedProfile.id,
          payload: {
            name: payload.name,
            slug: payload.slug,
            enabled: payload.enabled,
            is_default: payload.is_default,
            config: payload.config,
            secrets: payload.secrets,
          },
        });
      } else {
        const created = await createProfile.mutateAsync(payload);
        setSelectedProfileId(created.id);
        setDraftProfile(null);
        setIsCreating(false);
      }
      setProfileFeedback({ tone: "healthy", message: "Profile saved." });
    } catch (error) {
      setProfileFeedback({
        tone: "danger",
        message: error instanceof Error ? error.message : "Failed to save profile.",
      });
      throw error;
    }
  }

  async function handleTest(profile: OperatorConfigProfile) {
    const result = await testProfile.mutateAsync(profile.id);
    setTestResult(`${result.status}${result.message ? ` - ${result.message}` : ""}`);
  }

  async function handleSetDefault(profile: OperatorConfigProfile) {
    setProfileFeedback(null);
    try {
      await updateProfile.mutateAsync({
        profileId: profile.id,
        payload: { is_default: true },
      });
      setProfileFeedback({
        tone: "healthy",
        message: "Default profile updated.",
      });
    } catch (error) {
      setProfileFeedback({
        tone: "danger",
        message:
          error instanceof Error ? error.message : "Failed to update default profile.",
      });
    }
  }

  function handleDuplicateProfile(profile: OperatorConfigProfile) {
    setDraftProfile(createProfileDraft(activeKind, profiles, profile));
    setIsCreating(true);
    setSelectedProfileId(null);
    setTestResult(null);
    setProfileFeedback(null);
    setBindingFeedback(null);
  }

  async function confirmDeleteProfile(payload: {
    profileId: string;
    replacementDefaultProfileId?: string | null;
  }) {
    setProfileFeedback(null);
    try {
      await deleteProfile.mutateAsync(payload);
      if (selectedProfileId === payload.profileId) {
        setSelectedProfileId(null);
      }
      setPendingDeleteProfile(null);
      setTestResult(null);
      setProfileFeedback({ tone: "healthy", message: "Profile deleted." });
    } catch (error) {
      setProfileFeedback({
        tone: "danger",
          message: error instanceof Error ? error.message : "Failed to delete profile.",
      });
    }
  }

  return (
    <WorkspaceSurface
      data-testid="configuration-workspace"
      className="space-y-4 px-5 py-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
            Control plane
          </p>
          <h2 className="mt-2 text-lg font-semibold text-[var(--vz-text-primary)]">
            Configuration
          </h2>
        </div>
        <Button
          type="button"
          onClick={() => {
            setIsCreating(true);
            setSelectedProfileId(null);
            setDraftProfile(createProfileDraft(activeKind, profiles));
            setTestResult(null);
            setProfileFeedback(null);
            setBindingFeedback(null);
          }}
        >
          New profile
        </Button>
      </div>

      <div role="tablist" aria-label="Configuration categories" className="flex flex-wrap gap-2">
        {CONFIGURATION_KINDS.map((kind) => {
          const Icon = KIND_ICONS[kind];
          const selected = activeKind === kind;
          return (
            <button
              key={kind}
              type="button"
              role="tab"
              aria-selected={selected}
              className={[
                "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-semibold transition",
                selected
                  ? "border-[#8fd3ff] bg-[#123042] text-[#d8f2ff]"
                  : "border-white/10 bg-black/20 text-[#93a7c5] hover:text-[#f4f8ff]",
              ].join(" ")}
              onClick={() => {
                setActiveKind(kind);
                setSelectedProfileId(null);
                setIsCreating(false);
                setDraftProfile(null);
                setTestResult(null);
                setProfileFeedback(null);
                setBindingFeedback(null);
              }}
            >
              <Icon className="size-3.5" />
              {catalogLabels.get(kind) ?? labelForKind(kind)}
            </button>
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(220px,0.8fr)_minmax(0,1.8fr)]">
        <ProfileInventory
          profiles={profiles}
          selectedProfileId={isCreating ? null : selectedProfile?.id}
          bindingCountByProfileId={bindingCountByProfileId}
          onSelect={(profile) => {
            setIsCreating(false);
            setSelectedProfileId(profile.id);
            setTestResult(null);
            setProfileFeedback(null);
            setBindingFeedback(null);
          }}
          onSetDefault={(profile) => void handleSetDefault(profile)}
          onDuplicate={handleDuplicateProfile}
          onDelete={(profile) => setPendingDeleteProfile(profile)}
        />

        <div className="space-y-4">
          <ProfileEditor
            kind={activeKind}
            selectedProfile={isCreating ? null : selectedProfile}
            draftProfile={editorDraftProfile}
            catalog={catalog.data}
            onKindChange={(kind) => {
              setActiveKind(kind);
              setSelectedProfileId(null);
              setIsCreating(false);
              setDraftProfile(null);
              setTestResult(null);
              setProfileFeedback(null);
              setBindingFeedback(null);
            }}
            onSave={handleSave}
          />
          {profileFeedback ? (
            <div role="status" aria-live="polite">
              <StatusToneBadge tone={profileFeedback.tone}>
                {profileFeedback.message}
              </StatusToneBadge>
            </div>
          ) : null}
          {selectedProfile && !isCreating ? (
            <div className="flex flex-wrap items-center gap-2">
              <Button type="button" onClick={() => void handleTest(selectedProfile)}>
                Test profile
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => handleDuplicateProfile(selectedProfile)}
              >
                Duplicate profile
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => setPendingDeleteProfile(selectedProfile)}
              >
                Delete profile
              </Button>
              {testResult ? (
                <StatusToneBadge tone={testResult.startsWith("valid") ? "healthy" : "danger"}>
                  {testResult}
                </StatusToneBadge>
              ) : null}
            </div>
          ) : null}
          <ProfileBindingPanel
            kind={activeKind}
            profiles={profiles}
            bindings={bindings}
            cameras={cameras.map((camera) => ({
              id: camera.id,
              label: camera.name ?? camera.id,
            }))}
            sites={sites.map((site) => ({ id: site.id, label: site.name ?? site.id }))}
            edgeNodes={edgeNodes.map((node) => ({
              id: node.id,
              label: node.hostname ?? node.id,
            }))}
            onBind={async (payload) => {
              setBindingFeedback(null);
              try {
                await upsertBinding.mutateAsync(payload);
                setBindingFeedback({ tone: "healthy", message: "Binding saved." });
              } catch (error) {
                setBindingFeedback({
                  tone: "danger",
                  message:
                    error instanceof Error ? error.message : "Failed to bind profile.",
                });
                throw error;
              }
            }}
            onUnbind={async (bindingId) => {
              setBindingFeedback(null);
              try {
                await deleteBinding.mutateAsync(bindingId);
                setBindingFeedback({ tone: "healthy", message: "Binding removed." });
              } catch (error) {
                setBindingFeedback({
                  tone: "danger",
                  message:
                    error instanceof Error ? error.message : "Failed to remove binding.",
                });
                throw error;
              }
            }}
          />
          {bindingFeedback ? (
            <div role="status" aria-live="polite">
              <StatusToneBadge tone={bindingFeedback.tone}>
                {bindingFeedback.message}
              </StatusToneBadge>
            </div>
          ) : null}
          <EffectiveConfigurationPanel
            catalog={catalog.data}
            cameras={cameras.map((camera) => ({
              id: camera.id,
              label: camera.name ?? camera.id,
            }))}
            sites={sites.map((site) => ({ id: site.id, label: site.name ?? site.id }))}
            edgeNodes={edgeNodes.map((node) => ({
              id: node.id,
              label: node.hostname ?? node.id,
            }))}
          />
        </div>
      </div>
      {pendingDeleteProfile ? (
        <ProfileImpactDialog
          profile={pendingDeleteProfile}
          impact={profileImpactQuery.data}
          isLoading={profileImpactQuery.isLoading}
          replacementCandidates={profiles}
          onCancel={() => setPendingDeleteProfile(null)}
          onConfirm={confirmDeleteProfile}
        />
      ) : null}
    </WorkspaceSurface>
  );
}
