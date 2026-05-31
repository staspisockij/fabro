import type { ReactNode } from "react";
import { Switch } from "@headlessui/react";
import { PlusIcon, XMarkIcon } from "@heroicons/react/16/solid";
import {
  EnvironmentApiDockerfileSourceInlineTypeEnum,
  EnvironmentNetworkMode,
  EnvironmentProvider,
} from "@qltysh/fabro-api-client";
import type {
  CreateEnvironmentRequest,
  Environment,
  EnvironmentApiImageSettings,
  EnvironmentLifecycleSettings,
  EnvironmentNetworkSettings,
  EnvironmentResourcesSettings,
  EnvironmentVolumeSettings,
  ReplaceEnvironmentRequest,
} from "@qltysh/fabro-api-client";

import { Panel, Row } from "./settings-panel";
import { INPUT_CLASS } from "./ui";

// Environment ids are server-managed file names: lowercase, digits, hyphens.
const ENVIRONMENT_ID_PATTERN = /^[a-z0-9][a-z0-9-]{0,62}$/;

interface KeyValueEntry {
  key: string;
  value: string;
}

interface VolumeEntry {
  id: string;
  mountPath: string;
  subpath: string;
}

export interface EnvironmentFormValues {
  id: string;
  provider: EnvironmentProvider;
  dockerRef: string;
  dockerfile: string;
  cpu: string;
  memory: string;
  disk: string;
  networkMode: EnvironmentNetworkMode;
  allow: string;
  preserve: boolean;
  stopOnTerminal: boolean;
  autoStop: string;
  labels: KeyValueEntry[];
  envVars: KeyValueEntry[];
  volumes: VolumeEntry[];
}

export const EMPTY_ENVIRONMENT_FORM: EnvironmentFormValues = {
  id:             "",
  provider:       EnvironmentProvider.DOCKER,
  dockerRef:      "",
  dockerfile:     "",
  cpu:            "",
  memory:         "",
  disk:           "",
  networkMode:    EnvironmentNetworkMode.ALLOW_ALL,
  allow:          "",
  preserve:       false,
  stopOnTerminal: true,
  autoStop:       "",
  labels:         [],
  envVars:        [],
  volumes:        [],
};

export function environmentToFormValues(environment: Environment): EnvironmentFormValues {
  return {
    id:             environment.id,
    provider:       environment.provider,
    dockerRef:      environment.image.docker ?? "",
    dockerfile:     environment.image.dockerfile?.value ?? "",
    cpu:            environment.resources.cpu === null ? "" : String(environment.resources.cpu),
    memory:         environment.resources.memory ?? "",
    disk:           environment.resources.disk ?? "",
    networkMode:    environment.network.mode,
    allow:          environment.network.allow.join("\n"),
    preserve:       environment.lifecycle.preserve,
    stopOnTerminal: environment.lifecycle.stop_on_terminal,
    autoStop:       environment.lifecycle.auto_stop ?? "",
    labels:         entriesFromMap(environment.labels),
    envVars:        entriesFromMap(environment.env),
    volumes:        environment.volumes.map((volume) => ({
      id:        volume.id,
      mountPath: volume.mount_path,
      subpath:   volume.subpath ?? "",
    })),
  };
}

export function isEnvironmentFormValid(values: EnvironmentFormValues): boolean {
  if (!ENVIRONMENT_ID_PATTERN.test(values.id.trim())) return false;
  if (values.cpu.trim() !== "" && !Number.isFinite(Number(values.cpu))) return false;
  return true;
}

export function createRequestFromForm(values: EnvironmentFormValues): CreateEnvironmentRequest {
  return { id: values.id.trim(), ...settingsFromForm(values) };
}

export function replaceRequestFromForm(values: EnvironmentFormValues): ReplaceEnvironmentRequest {
  return settingsFromForm(values);
}

function settingsFromForm(values: EnvironmentFormValues): ReplaceEnvironmentRequest {
  return {
    provider:  values.provider,
    image:     imageFromForm(values),
    resources: resourcesFromForm(values),
    network:   networkFromForm(values),
    lifecycle: lifecycleFromForm(values),
    labels:    mapFromEntries(values.labels),
    volumes:   volumesFromForm(values),
    env:       mapFromEntries(values.envVars),
  };
}

function imageFromForm(values: EnvironmentFormValues): EnvironmentApiImageSettings {
  const dockerfile = values.dockerfile.trim();
  return {
    docker: values.dockerRef.trim() || null,
    dockerfile: dockerfile
      ? { type: EnvironmentApiDockerfileSourceInlineTypeEnum.INLINE, value: values.dockerfile }
      : null,
  };
}

function resourcesFromForm(values: EnvironmentFormValues): EnvironmentResourcesSettings {
  const cpu = values.cpu.trim();
  return {
    cpu:    cpu === "" ? null : Number(cpu),
    memory: values.memory.trim() || null,
    disk:   values.disk.trim() || null,
  };
}

function networkFromForm(values: EnvironmentFormValues): EnvironmentNetworkSettings {
  return {
    mode: values.networkMode,
    allow: values.allow
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line !== ""),
  };
}

function lifecycleFromForm(values: EnvironmentFormValues): EnvironmentLifecycleSettings {
  return {
    preserve:         values.preserve,
    stop_on_terminal: values.stopOnTerminal,
    auto_stop:        values.autoStop.trim() || null,
  };
}

function volumesFromForm(values: EnvironmentFormValues): EnvironmentVolumeSettings[] {
  return values.volumes
    .map((volume) => ({
      id:         volume.id.trim(),
      mount_path: volume.mountPath.trim(),
      subpath:    volume.subpath.trim() || null,
    }))
    .filter((volume) => volume.id !== "" && volume.mount_path !== "");
}

function entriesFromMap(map: { [key: string]: string }): KeyValueEntry[] {
  return Object.entries(map).map(([key, value]) => ({ key, value }));
}

function mapFromEntries(entries: KeyValueEntry[]): { [key: string]: string } {
  return Object.fromEntries(
    entries
      .map((entry): [string, string] => [entry.key.trim(), entry.value])
      .filter((entry) => entry[0] !== ""),
  );
}

function parseProvider(value: string): EnvironmentProvider {
  switch (value) {
    case EnvironmentProvider.LOCAL:
      return EnvironmentProvider.LOCAL;
    case EnvironmentProvider.DAYTONA:
      return EnvironmentProvider.DAYTONA;
    default:
      return EnvironmentProvider.DOCKER;
  }
}

function parseNetworkMode(value: string): EnvironmentNetworkMode {
  switch (value) {
    case EnvironmentNetworkMode.BLOCK:
      return EnvironmentNetworkMode.BLOCK;
    case EnvironmentNetworkMode.CIDR_ALLOW_LIST:
      return EnvironmentNetworkMode.CIDR_ALLOW_LIST;
    default:
      return EnvironmentNetworkMode.ALLOW_ALL;
  }
}

interface EnvironmentFormFieldsProps {
  values: EnvironmentFormValues;
  onChange: (values: EnvironmentFormValues) => void;
  lockId?: boolean;
}

export function EnvironmentFormFields({
  values,
  onChange,
  lockId = false,
}: EnvironmentFormFieldsProps) {
  function patch(partial: Partial<EnvironmentFormValues>) {
    onChange({ ...values, ...partial });
  }

  const idValid = ENVIRONMENT_ID_PATTERN.test(values.id.trim());

  return (
    <>
      <Panel title="Identity">
        <Row
          title={<Label required>ID</Label>}
          help="Lowercase identifier (letters, digits, hyphens). Runs select this environment by id. Cannot be changed after creation."
        >
          {lockId ? (
            <div className="font-mono text-sm text-fg">{values.id}</div>
          ) : (
            <input
              type="text"
              name="id"
              aria-label="Environment ID"
              value={values.id}
              onChange={(e) => patch({ id: e.target.value })}
              placeholder="fabro-dev"
              autoComplete="off"
              spellCheck={false}
              className={`${INPUT_CLASS} font-mono`}
            />
          )}
        </Row>
        <Row title={<Label required>Provider</Label>} help="Where runs using this environment execute.">
          <select
            name="provider"
            aria-label="Provider"
            value={values.provider}
            onChange={(e) => patch({ provider: parseProvider(e.target.value) })}
            className={INPUT_CLASS}
          >
            {Object.values(EnvironmentProvider)
              .filter((provider) => provider !== EnvironmentProvider.LOCAL)
              .map((provider) => (
                <option key={provider} value={provider}>
                  {provider}
                </option>
              ))}
          </select>
        </Row>
      </Panel>

      <Panel title="Image">
        <Row
          title={<Label optional>Image reference</Label>}
          help="Docker image or Daytona snapshot name (e.g. fabro-v11)."
        >
          <input
            type="text"
            name="docker_ref"
            aria-label="Image reference"
            value={values.dockerRef}
            onChange={(e) => patch({ dockerRef: e.target.value })}
            placeholder="ubuntu:24.04"
            autoComplete="off"
            spellCheck={false}
            className={`${INPUT_CLASS} font-mono`}
          />
        </Row>
        <Row
          title={<Label optional>Dockerfile</Label>}
          help="Inline Dockerfile contents. The REST API accepts inline Dockerfiles only — local paths are rejected."
        >
          <textarea
            name="dockerfile"
            aria-label="Dockerfile"
            value={values.dockerfile}
            onChange={(e) => patch({ dockerfile: e.target.value })}
            rows={5}
            placeholder={"FROM ubuntu:24.04\nRUN apt-get update && apt-get install -y git"}
            autoComplete="off"
            spellCheck={false}
            className={`${INPUT_CLASS} resize-y font-mono`}
          />
        </Row>
      </Panel>

      <Panel title="Resources">
        <Row title={<Label optional>CPU</Label>} help="Number of vCPUs. Leave blank for the provider default.">
          <input
            type="number"
            name="cpu"
            aria-label="CPU"
            value={values.cpu}
            onChange={(e) => patch({ cpu: e.target.value })}
            placeholder="8"
            min={0}
            step={1}
            autoComplete="off"
            className={`${INPUT_CLASS} font-mono`}
          />
        </Row>
        <Row title={<Label optional>Memory</Label>} help="Memory limit (e.g. 16GB). Leave blank for the provider default.">
          <input
            type="text"
            name="memory"
            aria-label="Memory"
            value={values.memory}
            onChange={(e) => patch({ memory: e.target.value })}
            placeholder="16GB"
            autoComplete="off"
            spellCheck={false}
            className={`${INPUT_CLASS} font-mono`}
          />
        </Row>
        <Row title={<Label optional>Disk</Label>} help="Disk limit (e.g. 20GB). Leave blank for the provider default.">
          <input
            type="text"
            name="disk"
            aria-label="Disk"
            value={values.disk}
            onChange={(e) => patch({ disk: e.target.value })}
            placeholder="20GB"
            autoComplete="off"
            spellCheck={false}
            className={`${INPUT_CLASS} font-mono`}
          />
        </Row>
      </Panel>

      <Panel title="Network">
        <Row title={<Label required>Mode</Label>} help="How network egress is restricted for runs in this environment.">
          <select
            name="network_mode"
            aria-label="Network mode"
            value={values.networkMode}
            onChange={(e) => patch({ networkMode: parseNetworkMode(e.target.value) })}
            className={INPUT_CLASS}
          >
            {Object.values(EnvironmentNetworkMode).map((mode) => (
              <option key={mode} value={mode}>
                {mode}
              </option>
            ))}
          </select>
        </Row>
        {values.networkMode === EnvironmentNetworkMode.CIDR_ALLOW_LIST ? (
          <Row
            title={<Label optional>Allowed CIDRs</Label>}
            help="One CIDR per line. Only egress to these ranges is permitted."
          >
            <textarea
              name="allow"
              aria-label="Allowed CIDRs"
              value={values.allow}
              onChange={(e) => patch({ allow: e.target.value })}
              rows={3}
              placeholder={"10.0.0.0/8\n192.168.0.0/16"}
              autoComplete="off"
              spellCheck={false}
              className={`${INPUT_CLASS} resize-y font-mono`}
            />
          </Row>
        ) : null}
      </Panel>

      <Panel title="Lifecycle">
        <Row title="Preserve" help="Keep the sandbox after the run finishes instead of tearing it down.">
          <ToggleSwitch
            checked={values.preserve}
            onChange={(preserve) => patch({ preserve })}
            label="Preserve sandbox after run"
          />
        </Row>
        <Row title="Stop on terminal" help="Stop the sandbox when the run reaches a terminal state.">
          <ToggleSwitch
            checked={values.stopOnTerminal}
            onChange={(stopOnTerminal) => patch({ stopOnTerminal })}
            label="Stop sandbox on terminal state"
          />
        </Row>
        <Row title={<Label optional>Auto-stop</Label>} help="Idle duration before the sandbox is stopped (e.g. 30m). Leave blank to disable.">
          <input
            type="text"
            name="auto_stop"
            aria-label="Auto-stop"
            value={values.autoStop}
            onChange={(e) => patch({ autoStop: e.target.value })}
            placeholder="30m"
            autoComplete="off"
            spellCheck={false}
            className={`${INPUT_CLASS} font-mono`}
          />
        </Row>
      </Panel>

      <Panel title="Labels">
        <div className="px-4 py-3.5">
          <p className="mb-3 text-xs/5 text-fg-3">
            Arbitrary key/value labels attached to the environment.
          </p>
          <KeyValueEditor
            entries={values.labels}
            onChange={(labels) => patch({ labels })}
            keyPlaceholder="team"
            valuePlaceholder="infra"
            addLabel="Add label"
          />
        </div>
      </Panel>

      <Panel title="Environment variables">
        <div className="px-4 py-3.5">
          <p className="mb-3 text-xs/5 text-fg-3">
            Variables injected into the sandbox for every run.
          </p>
          <KeyValueEditor
            entries={values.envVars}
            onChange={(envVars) => patch({ envVars })}
            keyPlaceholder="TZ"
            valuePlaceholder="UTC"
            addLabel="Add variable"
          />
        </div>
      </Panel>

      <Panel title="Volumes">
        <div className="px-4 py-3.5">
          <p className="mb-3 text-xs/5 text-fg-3">
            Named volumes mounted into the sandbox. Id and mount path are required.
          </p>
          <VolumeEditor
            volumes={values.volumes}
            onChange={(volumes) => patch({ volumes })}
          />
        </div>
      </Panel>

      {!lockId && values.id.trim() !== "" && !idValid ? (
        <p className="text-xs text-coral">
          ID must be lowercase letters, digits, or hyphens and start with a letter or digit.
        </p>
      ) : null}
    </>
  );
}

function KeyValueEditor({
  entries,
  onChange,
  keyPlaceholder,
  valuePlaceholder,
  addLabel,
}: {
  entries: KeyValueEntry[];
  onChange: (entries: KeyValueEntry[]) => void;
  keyPlaceholder: string;
  valuePlaceholder: string;
  addLabel: string;
}) {
  function update(index: number, partial: Partial<KeyValueEntry>) {
    onChange(entries.map((entry, i) => (i === index ? { ...entry, ...partial } : entry)));
  }

  return (
    <div className="space-y-2">
      {entries.map((entry, index) => (
        <div key={index} className="flex items-center gap-2">
          <input
            type="text"
            aria-label="Key"
            value={entry.key}
            onChange={(e) => update(index, { key: e.target.value })}
            placeholder={keyPlaceholder}
            autoComplete="off"
            spellCheck={false}
            className={`${INPUT_CLASS} font-mono`}
          />
          <input
            type="text"
            aria-label="Value"
            value={entry.value}
            onChange={(e) => update(index, { value: e.target.value })}
            placeholder={valuePlaceholder}
            autoComplete="off"
            spellCheck={false}
            className={`${INPUT_CLASS} font-mono`}
          />
          <RemoveButton onClick={() => onChange(entries.filter((_, i) => i !== index))} />
        </div>
      ))}
      <AddButton label={addLabel} onClick={() => onChange([...entries, { key: "", value: "" }])} />
    </div>
  );
}

function VolumeEditor({
  volumes,
  onChange,
}: {
  volumes: VolumeEntry[];
  onChange: (volumes: VolumeEntry[]) => void;
}) {
  function update(index: number, partial: Partial<VolumeEntry>) {
    onChange(volumes.map((volume, i) => (i === index ? { ...volume, ...partial } : volume)));
  }

  return (
    <div className="space-y-2">
      {volumes.map((volume, index) => (
        <div key={index} className="flex items-center gap-2">
          <input
            type="text"
            aria-label="Volume id"
            value={volume.id}
            onChange={(e) => update(index, { id: e.target.value })}
            placeholder="cache"
            autoComplete="off"
            spellCheck={false}
            className={`${INPUT_CLASS} font-mono`}
          />
          <input
            type="text"
            aria-label="Mount path"
            value={volume.mountPath}
            onChange={(e) => update(index, { mountPath: e.target.value })}
            placeholder="/cache"
            autoComplete="off"
            spellCheck={false}
            className={`${INPUT_CLASS} font-mono`}
          />
          <input
            type="text"
            aria-label="Subpath"
            value={volume.subpath}
            onChange={(e) => update(index, { subpath: e.target.value })}
            placeholder="subpath (optional)"
            autoComplete="off"
            spellCheck={false}
            className={`${INPUT_CLASS} font-mono`}
          />
          <RemoveButton onClick={() => onChange(volumes.filter((_, i) => i !== index))} />
        </div>
      ))}
      <AddButton
        label="Add volume"
        onClick={() => onChange([...volumes, { id: "", mountPath: "", subpath: "" }])}
      />
    </div>
  );
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded-md border border-line bg-panel/80 px-2.5 py-1 text-xs font-medium text-fg-3 transition-colors hover:border-line-strong hover:bg-panel hover:text-fg"
    >
      <PlusIcon className="size-3.5" aria-hidden="true" />
      {label}
    </button>
  );
}

function RemoveButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Remove row"
      title="Remove"
      className="flex size-9 shrink-0 items-center justify-center rounded-lg text-fg-muted transition-colors hover:bg-overlay hover:text-coral"
    >
      <XMarkIcon className="size-4" aria-hidden="true" />
    </button>
  );
}

function Label({
  children,
  required,
  optional,
}: {
  children: ReactNode;
  required?: boolean;
  optional?: boolean;
}) {
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span>{children}</span>
      {required ? (
        <span aria-label="required" className="text-coral">
          *
        </span>
      ) : null}
      {optional ? <span className="text-xs font-normal text-fg-muted">Optional</span> : null}
    </span>
  );
}

function ToggleSwitch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
}) {
  return (
    <Switch
      checked={checked}
      onChange={onChange}
      aria-label={label}
      className="group relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full bg-overlay-strong outline-1 -outline-offset-1 outline-line-strong transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-500 data-checked:bg-teal-500"
    >
      <span className="pointer-events-none inline-block size-4 translate-x-0.5 rounded-full bg-fg shadow-sm transition-transform duration-150 group-data-checked:translate-x-[1.125rem]" />
    </Switch>
  );
}
