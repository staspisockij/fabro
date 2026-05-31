import { useState } from "react";
import { Link } from "react-router";
import { useSWRConfig } from "swr";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/react";
import { PlusIcon } from "@heroicons/react/16/solid";
import { EllipsisVerticalIcon } from "@heroicons/react/20/solid";
import type { Environment } from "@qltysh/fabro-api-client";

import { ApiError, apiData, environmentsApi } from "../lib/api-client";
import { useEnvironments } from "../lib/queries";
import { queryKeys } from "../lib/query-keys";
import {
  Badge,
  Muted,
  Panel,
  PanelSkeleton,
  SettingsPageIntro,
} from "../components/settings-panel";
import { ConfirmDialog } from "../components/ui";
import { useToast } from "../components/toast";

// `default` is seeded and protected from deletion by the server; reflect that
// in the UI instead of letting the delete fail with a 409.
const PROTECTED_ID = "default";

// `local` is a reserved, in-memory environment (present only when the local
// sandbox provider is enabled). It cannot be edited or deleted.
const RESERVED_ID = "local";

const MENU_ITEM_CLASS =
  "flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-fg-3 transition-colors data-focus:bg-overlay data-focus:text-fg data-focus:outline-hidden disabled:cursor-not-allowed disabled:opacity-60";

const MENU_ITEM_DANGER_CLASS =
  "flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-coral transition-colors data-focus:bg-coral/10 data-focus:text-coral data-focus:outline-hidden disabled:cursor-not-allowed disabled:opacity-60";

export function meta() {
  return [{ title: "Environments — Fabro" }];
}

const DESCRIPTION =
  "Environments are server-managed runtime definitions — provider, image, resources, network, and lifecycle — that workflow runs select by id. They are operator policy stored on this Fabro server.";

export default function SettingsEnvironments() {
  const query = useEnvironments();

  return (
    <div className="space-y-6">
      <SettingsPageIntro
        description={DESCRIPTION}
        action={
          <Link
            to="/settings/environments/new"
            className="inline-flex items-center gap-1.5 rounded-md border border-line bg-panel/80 px-2.5 py-1 text-sm font-medium text-fg-3 transition-colors hover:border-line-strong hover:bg-panel hover:text-fg"
          >
            <PlusIcon className="size-3.5" aria-hidden="true" />
            New environment
          </Link>
        }
      />
      {query.data ? (
        <EnvironmentsPanel environments={query.data.data} />
      ) : query.error ? (
        <Panel title="Environments">
          <div className="px-4 py-6 text-sm text-fg-2">
            Couldn&apos;t load environments. Please try again.
          </div>
        </Panel>
      ) : (
        <PanelSkeleton />
      )}
    </div>
  );
}

function EnvironmentsPanel({ environments }: { environments: Environment[] }) {
  const { mutate } = useSWRConfig();
  const toast = useToast();
  const [pendingDelete, setPendingDelete] = useState<Environment | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function confirmDelete() {
    if (!pendingDelete) return;
    const target = pendingDelete;
    setDeleting(true);
    try {
      await apiData(() => environmentsApi.deleteEnvironment(target.id, target.revision));
      await mutate(queryKeys.environments.list());
      toast.push({ message: `Environment “${target.id}” deleted.` });
      setPendingDelete(null);
    } catch (cause) {
      toast.push({
        tone: "error",
        message:
          cause instanceof ApiError && cause.message
            ? cause.message
            : "Couldn't delete the environment. Please try again.",
      });
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <Panel title="Environments">
        {environments.length === 0 ? (
          <div className="px-4 py-6 text-sm text-fg-muted">
            No environments defined yet.
          </div>
        ) : (
          environments.map((environment) => (
            <EnvironmentRow
              key={environment.id}
              environment={environment}
              disabled={deleting}
              onDelete={() => setPendingDelete(environment)}
            />
          ))
        )}
      </Panel>
      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete environment"
        description={
          <>
            Delete{" "}
            <span className="font-mono text-fg-2">{pendingDelete?.id}</span>? Runs that
            select this environment will fail until it is recreated.
          </>
        }
        confirmLabel="Delete"
        pendingLabel="Deleting…"
        pending={deleting}
        onConfirm={confirmDelete}
        onCancel={() => {
          if (!deleting) setPendingDelete(null);
        }}
      />
    </>
  );
}

function EnvironmentRow({
  environment,
  disabled,
  onDelete,
}: {
  environment: Environment;
  disabled: boolean;
  onDelete: () => void;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)_auto] items-center gap-4 px-4 py-3.5">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="truncate font-mono text-sm text-fg" title={environment.id}>
            {environment.id}
          </span>
          <Badge>{environment.provider}</Badge>
          {environment.id === RESERVED_ID ? (
            <StatusTag>reserved</StatusTag>
          ) : environment.id === PROTECTED_ID ? (
            <StatusTag>protected</StatusTag>
          ) : null}
        </div>
        <div className="mt-0.5 truncate text-xs/5 text-fg-3">
          {resourcesSummary(environment)} · network {environment.network.mode}
        </div>
      </div>
      <div
        className="min-w-0 truncate font-mono text-xs text-fg-2"
        title={imageSummary(environment) ?? undefined}
      >
        {imageSummary(environment) ?? <Muted>No image</Muted>}
      </div>
      <RowMenu environment={environment} disabled={disabled} onDelete={onDelete} />
    </div>
  );
}

function imageSummary(environment: Environment): string | null {
  if (environment.image.docker) return environment.image.docker;
  if (environment.image.dockerfile) return "Dockerfile (inline)";
  return null;
}

function resourcesSummary(environment: Environment): string {
  const parts = [
    environment.resources.cpu === null ? null : `${environment.resources.cpu} CPU`,
    environment.resources.memory,
    environment.resources.disk,
  ].filter((part): part is string => Boolean(part));
  return parts.length > 0 ? parts.join(" · ") : "Default resources";
}

function StatusTag({ children }: { children: string }) {
  return (
    <span className="rounded-sm bg-overlay px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-fg-muted">
      {children}
    </span>
  );
}

function RowMenu({
  environment,
  disabled,
  onDelete,
}: {
  environment: Environment;
  disabled: boolean;
  onDelete: () => void;
}) {
  const reserved = environment.id === RESERVED_ID;
  const protectedFromDelete = environment.id === PROTECTED_ID;
  return (
    <Menu as="div" className="relative inline-block">
      <MenuButton
        type="button"
        disabled={disabled}
        aria-label={`Actions for ${environment.id}`}
        title="Actions"
        className="flex size-7 items-center justify-center rounded text-fg-muted transition-colors hover:bg-overlay hover:text-fg-3 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <EllipsisVerticalIcon className="size-4" aria-hidden="true" />
      </MenuButton>
      <MenuItems
        transition
        anchor={{ to: "bottom end", gap: 4 }}
        className="z-30 w-36 origin-top-right rounded-md bg-panel py-1 outline-1 -outline-offset-1 outline-line-strong transition data-closed:scale-95 data-closed:opacity-0 data-enter:duration-100 data-enter:ease-out data-leave:duration-75 data-leave:ease-in"
      >
        <MenuItem>
          {reserved ? (
            <button
              type="button"
              disabled
              title="The local environment is reserved and cannot be edited"
              className={MENU_ITEM_CLASS}
            >
              Edit
            </button>
          ) : (
            <Link
              to={`/settings/environments/${encodeURIComponent(environment.id)}/edit`}
              className={MENU_ITEM_CLASS}
            >
              Edit
            </Link>
          )}
        </MenuItem>
        <hr className="my-1 h-px border-0 bg-line" />
        <MenuItem>
          <button
            type="button"
            onClick={onDelete}
            disabled={disabled || protectedFromDelete || reserved}
            title={
              reserved
                ? "The local environment is reserved"
                : protectedFromDelete
                  ? "The default environment is protected"
                  : undefined
            }
            className={MENU_ITEM_DANGER_CLASS}
          >
            {reserved ? "Reserved" : protectedFromDelete ? "Protected" : "Delete"}
          </button>
        </MenuItem>
      </MenuItems>
    </Menu>
  );
}
