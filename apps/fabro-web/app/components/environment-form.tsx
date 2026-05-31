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
  ReplaceEnvironmentRequest,
} from "@qltysh/fabro-api-client";

import { Panel, Row } from "./settings-panel";
import { INPUT_CLASS } from "./ui";

// Environment ids are server-managed file names: lowercase, digits, hyphens.
const ENVIRONMENT_ID_PATTERN = /^[a-z0-9][a-z0-9-]{0,62}$/;

// Resource sliders pick a concrete value within a fixed range. Memory and disk
// are expressed in whole GB; the wire format keeps the `GB` suffix string.
const CPU = { min: 1, max: 8, step: 1, default: 4 };
const MEMORY = { min: 1, max: 16, step: 1, default: 8 };
const DISK = { min: 1, max: 20, step: 1, default: 16 };

interface KeyValueEntry {
  key: string;
  value: string;
}

export interface EnvironmentFormValues {
  id: string;
  provider: EnvironmentProvider;
  dockerRef: string;
  dockerfile: string;
  cpu: number;
  memory: number;
  disk: number;
  networkMode: EnvironmentNetworkMode;
  allow: string;
  preserve: boolean;
  stopOnTerminal: boolean;
  autoStop: string;
  labels: KeyValueEntry[];
  envVars: KeyValueEntry[];
}

export const EMPTY_ENVIRONMENT_FORM: EnvironmentFormValues = {
  id:             "",
  provider:       EnvironmentProvider.DOCKER,
  dockerRef:      "",
  dockerfile:     "",
  cpu:            CPU.default,
  memory:         MEMORY.default,
  disk:           DISK.default,
  networkMode:    EnvironmentNetworkMode.ALLOW_ALL,
  allow:          "",
  preserve:       false,
  stopOnTerminal: true,
  autoStop:       "",
  labels:         [],
  envVars:        [],
};

export function environmentToFormValues(environment: Environment): EnvironmentFormValues {
  return {
    id:             environment.id,
    provider:       environment.provider,
    dockerRef:      environment.image.docker ?? "",
    dockerfile:     environment.image.dockerfile?.value ?? "",
    cpu:            clampGb(environment.resources.cpu, CPU),
    memory:         parseGb(environment.resources.memory, MEMORY),
    disk:           parseGb(environment.resources.disk, DISK),
    networkMode:    environment.network.mode,
    allow:          environment.network.allow.join("\n"),
    preserve:       environment.lifecycle.preserve,
    stopOnTerminal: environment.lifecycle.stop_on_terminal,
    autoStop:       environment.lifecycle.auto_stop ?? "",
    labels:         entriesFromMap(environment.labels),
    envVars:        entriesFromMap(environment.env),
  };
}

export function isEnvironmentFormValid(values: EnvironmentFormValues): boolean {
  return ENVIRONMENT_ID_PATTERN.test(values.id.trim());
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
  return {
    cpu:    values.cpu,
    memory: `${values.memory}GB`,
    disk:   `${values.disk}GB`,
  };
}

interface ResourceRange {
  min: number;
  max: number;
  step: number;
  default: number;
}

// Snap a numeric value into the slider range, falling back to the default when
// the environment leaves the resource unset (provider default).
function clampGb(value: number | null, range: ResourceRange): number {
  if (value === null) return range.default;
  return Math.min(range.max, Math.max(range.min, Math.round(value)));
}

// Parse a size string ("16GB", "512MiB", or a bare integer interpreted as GB)
// into whole GB within the slider range. Existing values may use other units or
// fall outside the range, so the result is rounded and clamped.
function parseGb(value: string | null, range: ResourceRange): number {
  if (value === null) return range.default;
  const match = value.trim().match(/^([\d.]+)\s*([a-zA-Z]*)$/);
  if (!match) return range.default;
  const amount = Number(match[1]);
  if (!Number.isFinite(amount)) return range.default;
  const perGb: { [unit: string]: number } = {
    "": 1, g: 1, gb: 1, gib: 1,
    m: 1 / 1000, mb: 1 / 1000, mib: 1 / 1000,
    t: 1000, tb: 1000, tib: 1000,
  };
  const factor = perGb[match[2].toLowerCase()] ?? 1;
  return clampGb(amount * factor, range);
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
        <Row title="CPU" help="Number of vCPUs allocated to each run.">
          <ResourceSlider
            ariaLabel="CPU"
            range={CPU}
            value={values.cpu}
            onChange={(cpu) => patch({ cpu })}
            format={(n) => `${n} CPU`}
          />
        </Row>
        <Row title="Memory" help="Memory limit for each run.">
          <ResourceSlider
            ariaLabel="Memory"
            range={MEMORY}
            value={values.memory}
            onChange={(memory) => patch({ memory })}
            format={(n) => `${n} GB`}
          />
        </Row>
        <Row title="Disk" help="Disk limit for each run.">
          <ResourceSlider
            ariaLabel="Disk"
            range={DISK}
            value={values.disk}
            onChange={(disk) => patch({ disk })}
            format={(n) => `${n} GB`}
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

function ResourceSlider({
  value,
  range,
  ariaLabel,
  format,
  onChange,
}: {
  value: number;
  range: ResourceRange;
  ariaLabel: string;
  format: (value: number) => string;
  onChange: (value: number) => void;
}) {
  const fill = ((value - range.min) / (range.max - range.min)) * 100;
  return (
    <div className="flex items-center gap-4">
      <div className="relative h-4 flex-1">
        <div className="pointer-events-none absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-overlay-strong">
          <div className="h-full rounded-full bg-teal-500" style={{ width: `${fill}%` }} />
        </div>
        <input
          type="range"
          aria-label={ariaLabel}
          value={value}
          min={range.min}
          max={range.max}
          step={range.step}
          onChange={(e) => onChange(Number(e.target.value))}
          className="relative h-4 w-full cursor-pointer appearance-none bg-transparent focus-visible:outline-none [&::-moz-range-thumb]:size-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-fg [&::-moz-range-thumb]:shadow-sm [&::-moz-range-track]:h-1.5 [&::-moz-range-track]:rounded-full [&::-moz-range-track]:bg-transparent [&::-webkit-slider-runnable-track]:h-1.5 [&::-webkit-slider-runnable-track]:rounded-full [&::-webkit-slider-runnable-track]:bg-transparent [&::-webkit-slider-thumb]:-mt-[5px] [&::-webkit-slider-thumb]:size-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-fg [&::-webkit-slider-thumb]:shadow-sm [&::-webkit-slider-thumb]:outline [&::-webkit-slider-thumb]:outline-1 [&::-webkit-slider-thumb]:-outline-offset-1 [&::-webkit-slider-thumb]:outline-line-strong focus-visible:[&::-webkit-slider-thumb]:outline-2 focus-visible:[&::-webkit-slider-thumb]:outline-teal-500"
        />
      </div>
      <output className="w-16 shrink-0 text-right font-mono text-sm tabular-nums text-fg">
        {format(value)}
      </output>
    </div>
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
