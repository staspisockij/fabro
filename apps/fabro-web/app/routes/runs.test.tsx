import { describe, expect, test } from "bun:test";
import type { BoardColumn, Run } from "@qltysh/fabro-api-client";

import {
  buildBoardColumns,
  runsQuickStartCommands,
  shouldRefreshBoardForEvent,
} from "./runs";

function boardRun(id: string, column: BoardColumn, questionText?: string): Run {
  const status =
    column === "blocked"
      ? { kind: "blocked" as const, blocked_reason: "human_input_required" }
      : column === "succeeded"
        ? { kind: "succeeded" as const, reason: "completed" }
        : column === "failed"
          ? { kind: "failed" as const, reason: "workflow_error" }
          : column === "initializing"
            ? { kind: "starting" as const }
            : { kind: "running" as const };
  return {
    id,
    goal:             `Run ${id}`,
    title:            `Run ${id}`,
    workflow:         { slug: "test", name: "Test" },
    automation:       null,
    repository:       { name: "repo", origin_url: null, provider: "unknown" },
    created_by:       null,
    origin:           { kind: "api" },
    labels:           {},
    lifecycle:        {
      status,
      pending_control: null,
      queue_position:  null,
      error:           null,
      archived:        false,
      archived_at:     null,
    },
    sandbox:          null,
    models:           [],
    source_directory: null,
    timestamps:       {
      created_at:     "2026-04-19T12:00:00Z",
      started_at:     null,
      last_event_at:  null,
      completed_at:   null,
    },
    billing:          null,
    diff:             null,
    pull_request:     null,
    current_question: questionText ? { text: questionText } : null,
    superseded_by:    null,
    links:            { web: null },
  };
}

describe("runs route board mapping", () => {
  test("keeps blocked runs in the blocked lane and preserves question text", () => {
    const columns = buildBoardColumns({
      columns: [
        { id: "initializing", name: "Initializing" },
        { id: "running", name: "Running" },
        { id: "blocked", name: "Blocked" },
        { id: "succeeded", name: "Succeeded" },
        { id: "failed", name: "Failed" },
      ],
      data: [
        boardRun("paused-run", "running"),
        boardRun("blocked-run", "blocked", "Older unresolved question?"),
      ],
      meta: { has_more: false },
    });

    expect(columns.find((column) => column.id === "running")?.items.map((item) => item.id)).toContain("paused-run");
    expect(columns.find((column) => column.id === "blocked")?.items.map((item) => item.id)).toContain("blocked-run");
    expect(columns.find((column) => column.id === "blocked")?.items[0]?.question).toBe("Older unresolved question?");
  });

  test("renders the five board columns returned by the API", () => {
    const columns = buildBoardColumns({
      columns: [
        { id: "initializing", name: "Initializing" },
        { id: "running", name: "Running" },
        { id: "blocked", name: "Blocked" },
        { id: "succeeded", name: "Succeeded" },
        { id: "failed", name: "Failed" },
      ],
      data: [boardRun("succeeded-run", "succeeded")],
      meta: { has_more: false },
    });

    expect(columns.map((column) => column.id)).toEqual([
      "initializing",
      "running",
      "blocked",
      "succeeded",
      "failed",
    ]);
    expect(
      columns.find((column) => column.id === "succeeded")?.items.map((item) => item.id),
    ).toEqual(["succeeded-run"]);
  });

  test("omits archived runs because archived is not a board column", () => {
    const archivedRun = boardRun("archived-run", "succeeded");
    archivedRun.lifecycle.archived = true;
    archivedRun.lifecycle.archived_at = "2026-04-19T12:05:00Z";

    const columns = buildBoardColumns({
      columns: [
        { id: "initializing", name: "Initializing" },
        { id: "running", name: "Running" },
        { id: "blocked", name: "Blocked" },
        { id: "succeeded", name: "Succeeded" },
        { id: "failed", name: "Failed" },
      ],
      data: [boardRun("succeeded-run", "succeeded"), archivedRun],
      meta: { has_more: false },
    });

    expect(columns.map((column) => column.id)).toEqual([
      "initializing",
      "running",
      "blocked",
      "succeeded",
      "failed",
    ]);
    expect(columns.flatMap((column) => column.items).map((item) => item.id)).toEqual(["succeeded-run"]);
  });

  test("refreshes for blocked status and interview events", () => {
    expect(shouldRefreshBoardForEvent("run.queued")).toBe(true);
    expect(shouldRefreshBoardForEvent("run.blocked")).toBe(true);
    expect(shouldRefreshBoardForEvent("run.unblocked")).toBe(true);
    expect(shouldRefreshBoardForEvent("run.archived")).toBe(true);
    expect(shouldRefreshBoardForEvent("run.unarchived")).toBe(true);
    expect(shouldRefreshBoardForEvent("run.title.updated")).toBe(true);
    expect(shouldRefreshBoardForEvent("interview.started")).toBe(true);
    expect(shouldRefreshBoardForEvent("interview.completed")).toBe(true);
    expect(shouldRefreshBoardForEvent("run.created")).toBe(false);
  });

  test("includes the configured server argument for GitHub-auth quick starts", () => {
    expect(runsQuickStartCommands(true, "http://127.0.0.1:32276")).toEqual([
      "fabro auth login --server http://127.0.0.1:32276",
      "fabro repo init",
      "fabro run hello",
    ]);
  });

  test("does not show a placeholder server when system info is unavailable", () => {
    expect(runsQuickStartCommands(true)).toEqual([
      "fabro repo init",
      "fabro run hello",
    ]);
  });
});
