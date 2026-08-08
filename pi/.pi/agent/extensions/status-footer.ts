import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { isAbsolute, relative, resolve, sep } from "node:path";

import { SettingsManager, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { truncateToWidth, visibleWidth } from "@earendil-works/pi-tui";

const STATUS_REFRESH_MS = 750;
const CODEX_USAGE_REFRESH_MS = 60_000;
const CODEX_USAGE_TIMEOUT_MS = 10_000;
const CYAN = (text: string) => `\x1b[36m${text}\x1b[39m`;
const SOFT_TEXT = (text: string) => `\x1b[38;2;144;168;148m${text}\x1b[39m`;

interface GitStatus {
	untracked: boolean;
	unstaged: boolean;
	staged: boolean;
}

interface UsageTotals {
	input: number;
	output: number;
	cacheRead: number;
	cacheWrite: number;
	cost: number;
	latestCacheHitRate?: number;
}

interface RateLimitWindow {
	usedPercent: number;
	windowDurationMins: number | null;
	resetsAt: number | null;
}

interface CreditsSnapshot {
	hasCredits: boolean;
	unlimited: boolean;
	balance: string | null;
}

interface RateLimitSnapshot {
	limitId: string | null;
	limitName: string | null;
	primary: RateLimitWindow | null;
	secondary: RateLimitWindow | null;
	credits: CreditsSnapshot | null;
	individualLimit: {
		limit: string;
		remainingPercent: number;
		resetsAt: number;
		used: string;
	} | null;
	spendControlReached: boolean | null;
	planType: string | null;
	rateLimitReachedType: string | null;
}

interface RateLimitResetCredit {
	id: string;
	status: string;
	grantedAt: number;
	expiresAt: number | null;
	title: string | null;
	description: string | null;
}

interface CodexUsage {
	rateLimits: RateLimitSnapshot;
	rateLimitsByLimitId: Record<string, RateLimitSnapshot> | null;
	rateLimitResetCredits: {
		availableCount: number;
		credits: RateLimitResetCredit[] | null;
	} | null;
}

function formatTokens(count: number): string {
	if (count < 1_000) return count.toString();
	if (count < 10_000) return `${(count / 1_000).toFixed(1)}k`;
	if (count < 1_000_000) return `${Math.round(count / 1_000)}k`;
	if (count < 10_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
	return `${Math.round(count / 1_000_000)}M`;
}

function formatCwd(cwd: string, home: string | undefined): string {
	if (!home) return cwd;

	const resolvedCwd = resolve(cwd);
	const resolvedHome = resolve(home);
	const relativeToHome = relative(resolvedHome, resolvedCwd);
	const isInsideHome =
		relativeToHome === "" ||
		(relativeToHome !== ".." && !relativeToHome.startsWith(`..${sep}`) && !isAbsolute(relativeToHome));

	if (!isInsideHome) return cwd;
	return relativeToHome === "" ? "~" : `~${sep}${relativeToHome}`;
}

function parseGitStatus(output: string): GitStatus {
	const status: GitStatus = { untracked: false, unstaged: false, staged: false };

	for (const line of output.split("\n")) {
		if (line.length < 2) continue;
		if (line.startsWith("??")) status.untracked = true;
		if (line[1] !== " " && line[1] !== "?") status.unstaged = true;
		if (line[0] !== " " && line[0] !== "?") status.staged = true;
	}

	return status;
}

function sanitizeStatusText(text: string): string {
	return text.replace(/[\r\n\t]/g, " ").replace(/ +/g, " ").trim();
}

function formatTimestamp(timestamp: number | null): string {
	if (timestamp === null) return "unknown";
	return new Date(timestamp * 1_000).toLocaleString(undefined, {
		year: "numeric",
		month: "short",
		day: "numeric",
		hour: "numeric",
		minute: "2-digit",
		timeZoneName: "short",
	});
}

function formatWindow(window: RateLimitWindow | null): string {
	if (!window) return "unavailable";
	const remaining = Math.max(0, 100 - window.usedPercent);
	const duration = window.windowDurationMins === null
		? "unknown window"
		: window.windowDurationMins % 1_440 === 0
			? `${window.windowDurationMins / 1_440} day window`
			: `${window.windowDurationMins} minute window`;
	return `${window.usedPercent}% used, ${remaining}% remaining (${duration}; resets ${formatTimestamp(window.resetsAt)})`;
}

function formatCodexUsage(usage: CodexUsage): string {
	const limits = usage.rateLimits;
	const credits = limits.credits;
	const resetSummary = usage.rateLimitResetCredits;
	const lines = [
		"OpenAI Codex account usage",
		`Plan type: ${limits.planType ?? "unknown"}`,
		`Subscription usage: ${formatWindow(limits.primary)}`,
	];

	if (limits.secondary) lines.push(`Secondary limit: ${formatWindow(limits.secondary)}`);
	lines.push(`Limit reached: ${limits.rateLimitReachedType ? `Yes (${limits.rateLimitReachedType})` : "No"}`);

	if (credits) {
		const balance = credits.unlimited ? "unlimited" : credits.balance ?? "unknown";
		lines.push(`Extra credit balance: ${balance}${credits.hasCredits ? " (available)" : " (none available)"}`);
	} else {
		lines.push("Extra credit balance: unavailable");
	}

	if (limits.individualLimit) {
		lines.push(
			`Individual spend limit: ${limits.individualLimit.used} used of ${limits.individualLimit.limit}; ` +
				`${limits.individualLimit.remainingPercent}% remaining; resets ${formatTimestamp(limits.individualLimit.resetsAt)}`,
		);
	}
	lines.push(`Spend control reached: ${limits.spendControlReached === null ? "Unknown" : limits.spendControlReached ? "Yes" : "No"}`);
	lines.push(`Usage resets available: ${resetSummary?.availableCount ?? 0}`);

	for (const reset of resetSummary?.credits ?? []) {
		const title = reset.title ?? "Usage reset";
		const description = reset.description ? ` — ${reset.description}` : "";
		lines.push(`  • ${title} (${reset.status}; expires ${formatTimestamp(reset.expiresAt)})${description}`);
	}

	const additionalLimits = Object.entries(usage.rateLimitsByLimitId ?? {}).filter(
		([id]) => id !== limits.limitId,
	);
	for (const [id, snapshot] of additionalLimits) {
		lines.push(`${snapshot.limitName ?? id}: ${formatWindow(snapshot.primary)}`);
	}

	lines.push("Source: the account currently signed into the Codex CLI.");
	return lines.join("\n");
}

function requestCodex<T>(cwd: string, method: string, params: Record<string, unknown>): Promise<T> {
	return new Promise((resolveRequest, rejectRequest) => {
		const child = spawn("codex", ["app-server", "--listen", "stdio://"], {
			cwd,
			stdio: ["pipe", "pipe", "ignore"],
		});
		let settled = false;
		let stdout = "";

		const finish = (error?: Error, result?: T) => {
			if (settled) return;
			settled = true;
			clearTimeout(timeout);
			child.kill();
			if (error) rejectRequest(error);
			else resolveRequest(result!);
		};
		const send = (message: unknown) => child.stdin.write(`${JSON.stringify(message)}\n`);
		const timeout = setTimeout(
			() => finish(new Error("Timed out while reading Codex account usage")),
			CODEX_USAGE_TIMEOUT_MS,
		);

		child.on("error", (error) => finish(new Error(`Could not start Codex CLI: ${error.message}`)));
		child.on("close", (code) => {
			if (!settled) finish(new Error(`Codex usage service exited before responding (${code ?? "unknown"})`));
		});
		child.stdout.on("data", (chunk: Buffer) => {
			stdout += chunk.toString("utf8");
			let newline;
			while ((newline = stdout.indexOf("\n")) >= 0) {
				const line = stdout.slice(0, newline);
				stdout = stdout.slice(newline + 1);
				if (!line.trim()) continue;

				let message: { id?: number; result?: T; error?: { message?: string } };
				try {
					message = JSON.parse(line);
				} catch {
					continue;
				}

				if (message.id === 1 && message.result !== undefined) {
					send({ method: "initialized", params: {} });
					send({ id: 2, method, params });
				} else if (message.id === 2) {
					if (message.error) finish(new Error(message.error.message ?? "Codex usage request failed"));
					else if (message.result) finish(undefined, message.result);
				}
			}
		});

		send({
			id: 1,
			method: "initialize",
			params: {
				clientInfo: { name: "pi-status-footer", version: "1.0.0" },
				capabilities: {},
			},
		});
	});
}

function readCodexUsage(cwd: string): Promise<CodexUsage> {
	return requestCodex<CodexUsage>(cwd, "account/rateLimits/read", {});
}

function consumeCodexUsageReset(cwd: string, creditId: string | undefined): Promise<{ outcome: string }> {
	return requestCodex<{ outcome: string }>(cwd, "account/rateLimitResetCredit/consume", {
		creditId,
		idempotencyKey: randomUUID(),
	});
}

export default function (pi: ExtensionAPI) {
	let codexUsage: CodexUsage | undefined;
	let codexUsageUpdatedAt = 0;
	let codexUsagePromise: Promise<CodexUsage> | undefined;
	let requestFooterRender: (() => void) | undefined;
	let currentCwd = process.cwd();

	const refreshCodexUsage = async (force = false): Promise<CodexUsage> => {
		if (!force && codexUsage && Date.now() - codexUsageUpdatedAt < CODEX_USAGE_REFRESH_MS) return codexUsage;
		if (codexUsagePromise) return codexUsagePromise;

		codexUsagePromise = readCodexUsage(currentCwd);
		try {
			codexUsage = await codexUsagePromise;
			codexUsageUpdatedAt = Date.now();
			requestFooterRender?.();
			return codexUsage;
		} finally {
			codexUsagePromise = undefined;
		}
	};

	pi.registerCommand("usage", {
		description: "Show OpenAI Codex subscription usage, limits, credits, and resets",
		handler: async (_args, ctx) => {
			ctx.ui.notify("Refreshing Codex account usage...", "info");
			try {
				const usage = await refreshCodexUsage(true);
				ctx.ui.notify(formatCodexUsage(usage), "info");
			} catch (error) {
				const message = error instanceof Error ? error.message : String(error);
				ctx.ui.notify(`Could not read Codex account usage: ${message}`, "error");
			}
		},
	});

	pi.registerCommand("usage-reset", {
		description: "Redeem an available OpenAI Codex usage reset",
		handler: async (_args, ctx) => {
			let usage: CodexUsage;
			try {
				usage = await refreshCodexUsage(true);
			} catch (error) {
				const message = error instanceof Error ? error.message : String(error);
				ctx.ui.notify(`Could not read Codex account usage: ${message}`, "error");
				return;
			}

			const summary = usage.rateLimitResetCredits;
			if (!summary || summary.availableCount < 1) {
				ctx.ui.notify("No Codex usage resets are available.", "warning");
				return;
			}

			const availableCredits = (summary.credits ?? []).filter((credit) => credit.status === "available");
			let selectedCredit: RateLimitResetCredit | undefined;
			if (availableCredits.length === 1) {
				selectedCredit = availableCredits[0];
			} else if (availableCredits.length > 1) {
				const labels = availableCredits.map((credit, index) => {
					const title = credit.title ?? `Usage reset ${index + 1}`;
					return `${title} — expires ${formatTimestamp(credit.expiresAt)}`;
				});
				const selected = await ctx.ui.select("Choose a Codex usage reset to redeem:", labels);
				if (!selected) return;
				selectedCredit = availableCredits[labels.indexOf(selected)];
			}

			const used = usage.rateLimits.primary?.usedPercent;
			const usageText = used === undefined ? "Current usage is unavailable." : `Current subscription usage is ${used}% used.`;
			const resetText = selectedCredit
				? `${selectedCredit.title ?? "The selected reset"} expires ${formatTimestamp(selectedCredit.expiresAt)}.`
				: `Codex will choose one of your ${summary.availableCount} available resets.`;
			const confirmed = await ctx.ui.confirm(
				"Redeem Codex usage reset?",
				`${usageText}\n${resetText}\nThis consumes one reset and cannot be undone.`,
			);
			if (!confirmed) {
				ctx.ui.notify("Usage reset cancelled.", "info");
				return;
			}

			try {
				const result = await consumeCodexUsageReset(currentCwd, selectedCredit?.id);
				switch (result.outcome) {
					case "reset": {
						const refreshed = await refreshCodexUsage(true);
						ctx.ui.notify(`Codex usage reset successfully.\n\n${formatCodexUsage(refreshed)}`, "info");
						break;
					}
					case "nothingToReset":
						ctx.ui.notify("Codex reports that the current usage window does not need a reset.", "warning");
						break;
					case "noCredit":
						ctx.ui.notify("Codex reports that no usage reset is available.", "warning");
						break;
					case "alreadyRedeemed":
						ctx.ui.notify("This reset request was already redeemed successfully.", "info");
						break;
					default:
						ctx.ui.notify(`Codex returned an unknown reset result: ${result.outcome}`, "warning");
				}
			} catch (error) {
				const message = error instanceof Error ? error.message : String(error);
				ctx.ui.notify(`Could not reset Codex usage: ${message}`, "error");
			}
		},
	});

	pi.on("agent_settled", (_event, ctx) => {
		if (ctx.model?.provider === "openai-codex") void refreshCodexUsage().catch(() => {});
	});

	pi.on("session_start", (_event, ctx) => {
		currentCwd = ctx.cwd;
		if (ctx.mode !== "tui") return;

		const settingsManager = SettingsManager.create(ctx.cwd, undefined, {
			projectTrusted: ctx.isProjectTrusted(),
		});

		ctx.ui.setFooter((tui, theme, footerData) => {
			requestFooterRender = () => tui.requestRender();
			let gitStatus: GitStatus = { untracked: false, unstaged: false, staged: false };
			let autoCompactEnabled = settingsManager.getCompactionEnabled();
			let refreshInFlight = false;
			let settingsRefreshInFlight = false;
			let lastRefresh = 0;
			let lastSettingsRefresh = Date.now();
			let disposed = false;

			const refreshGitStatus = async () => {
				if (refreshInFlight || disposed) return;
				refreshInFlight = true;
				lastRefresh = Date.now();

				try {
					const result = await pi.exec("git", ["status", "--porcelain"], {
						cwd: ctx.cwd,
						timeout: 1_500,
					});
					const next = result.code === 0 ? parseGitStatus(result.stdout) : { untracked: false, unstaged: false, staged: false };
					if (
						next.untracked !== gitStatus.untracked ||
						next.unstaged !== gitStatus.unstaged ||
						next.staged !== gitStatus.staged
					) {
						gitStatus = next;
						if (!disposed) tui.requestRender();
					}
				} catch {
					gitStatus = { untracked: false, unstaged: false, staged: false };
				} finally {
					refreshInFlight = false;
				}
			};

			const refreshAutoCompaction = async () => {
				if (settingsRefreshInFlight || disposed) return;
				settingsRefreshInFlight = true;
				lastSettingsRefresh = Date.now();

				try {
					await settingsManager.reload();
					const next = settingsManager.getCompactionEnabled();
					if (next !== autoCompactEnabled) {
						autoCompactEnabled = next;
						if (!disposed) tui.requestRender();
					}
				} finally {
					settingsRefreshInFlight = false;
				}
			};

			const unsubscribeBranch = footerData.onBranchChange(() => {
				lastRefresh = 0;
				void refreshGitStatus();
				tui.requestRender();
			});
			void refreshGitStatus();
			if (ctx.model?.provider === "openai-codex") void refreshCodexUsage().catch(() => {});

			return {
				dispose() {
					disposed = true;
					requestFooterRender = undefined;
					unsubscribeBranch();
				},
				invalidate() {},
				render(width: number): string[] {
					if (Date.now() - lastRefresh >= STATUS_REFRESH_MS) void refreshGitStatus();
					if (Date.now() - lastSettingsRefresh >= STATUS_REFRESH_MS) void refreshAutoCompaction();
					if (
						ctx.model?.provider === "openai-codex" &&
						Date.now() - codexUsageUpdatedAt >= CODEX_USAGE_REFRESH_MS
					) {
						void refreshCodexUsage().catch(() => {});
					}

					const totals: UsageTotals = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, cost: 0 };
					for (const entry of ctx.sessionManager.getEntries()) {
						let usage;
						if (entry.type === "message" && entry.message.role === "assistant") {
							usage = entry.message.usage;
							const promptTokens = usage.input + usage.cacheRead + usage.cacheWrite;
							totals.latestCacheHitRate = promptTokens > 0 ? (usage.cacheRead / promptTokens) * 100 : undefined;
						} else if (entry.type === "message" && entry.message.role === "toolResult") {
							usage = entry.message.usage;
						} else if (entry.type === "branch_summary" || entry.type === "compaction") {
							usage = entry.usage;
						}

						if (usage) {
							totals.input += usage.input;
							totals.output += usage.output;
							totals.cacheRead += usage.cacheRead;
							totals.cacheWrite += usage.cacheWrite;
							totals.cost += usage.cost.total;
						}
					}

					const branch = footerData.getGitBranch();
					let location = theme.fg("accent", formatCwd(ctx.sessionManager.getCwd(), process.env.HOME || process.env.USERPROFILE));
					if (branch) {
						let circles = "";
						if (gitStatus.untracked) circles += theme.fg("error", "●");
						if (gitStatus.unstaged) circles += CYAN("●");
						if (gitStatus.staged) circles += theme.fg("success", "●");
						location += SOFT_TEXT(" (") + theme.fg("warning", branch) + (circles ? ` ${circles}` : "") + SOFT_TEXT(")");
					}

					const sessionName = ctx.sessionManager.getSessionName();
					if (sessionName) location += SOFT_TEXT(" • ") + SOFT_TEXT(sessionName);

					const part = (label: string, value: string) => theme.fg("accent", label) + SOFT_TEXT(value);
					const stats: string[] = [];
					if (totals.input) stats.push(part("↑", formatTokens(totals.input)));
					if (totals.output) stats.push(part("↓", formatTokens(totals.output)));
					if (totals.cacheRead) stats.push(part("R", formatTokens(totals.cacheRead)));
					if (totals.cacheWrite) stats.push(part("W", formatTokens(totals.cacheWrite)));
					if ((totals.cacheRead || totals.cacheWrite) && totals.latestCacheHitRate !== undefined) {
						stats.push(part("CH", `${totals.latestCacheHitRate.toFixed(1)}%`));
					}

					const subscriptionProvider = ctx.model?.provider === "openai-codex" || ctx.model?.provider === "github-copilot" || ctx.model?.provider === "kimi-coding";
					if (totals.cost || subscriptionProvider) {
						let cost = theme.fg("success", `$${totals.cost.toFixed(3)}`);
						if (subscriptionProvider) {
							cost += theme.fg("success", " (");
							if (ctx.model?.provider === "openai-codex" && codexUsage?.rateLimits.primary) {
								const limits = codexUsage.rateLimits;
								const used = limits.primary.usedPercent;
								const subColor = limits.rateLimitReachedType || used > 90
									? "error"
									: used >= 80
										? "warning"
										: "success";
								const resets = codexUsage.rateLimitResetCredits?.availableCount ?? 0;
								cost += theme.fg(subColor, `sub ${used}%`);
								cost += resets > 0 ? theme.fg("warning", ` ${resets}🔄`) : SOFT_TEXT(` ${resets}🔄`);
							} else {
								cost += theme.fg("success", "sub");
							}
							cost += theme.fg("success", ")");
						}
						stats.push(cost);
					}

					const context = ctx.getContextUsage();
					const contextWindow = context?.contextWindow ?? ctx.model?.contextWindow ?? 0;
					const contextValue = context?.percent ?? 0;
					const autoIndicator = autoCompactEnabled ? " (auto)" : "";
					const contextText = context?.percent === null || context === undefined
						? `?/${formatTokens(contextWindow)}${autoIndicator}`
						: `${context.percent.toFixed(1)}%/${formatTokens(contextWindow)}${autoIndicator}`;
					stats.push(theme.fg(contextValue > 90 ? "error" : contextValue > 70 ? "warning" : "success", contextText));

					let left = stats.join(" ");
					if (visibleWidth(left) > width) left = truncateToWidth(left, width, SOFT_TEXT("..."));

					let right = theme.bold(theme.fg("accent", ctx.model?.id || "no-model"));
					if (ctx.model?.reasoning) {
						const level = ctx.thinkingLevel || "off";
						const thinkingColor = {
							off: "thinkingOff",
							minimal: "thinkingMinimal",
							low: "thinkingLow",
							medium: "thinkingMedium",
							high: "thinkingHigh",
							xhigh: "thinkingXhigh",
							max: "thinkingMax",
						} as const;
						right += SOFT_TEXT(" • ") + theme.fg(thinkingColor[level], level === "off" ? "thinking off" : level);
					}

					if (footerData.getAvailableProviderCount() > 1 && ctx.model) {
						const withProvider = SOFT_TEXT(`(${ctx.model.provider}) `) + right;
						if (visibleWidth(left) + 2 + visibleWidth(withProvider) <= width) right = withProvider;
					}

					const availableRight = width - visibleWidth(left) - 2;
					if (availableRight > 0 && visibleWidth(right) > availableRight) {
						right = truncateToWidth(right, availableRight, "");
					}
					const padding = " ".repeat(Math.max(0, width - visibleWidth(left) - visibleWidth(right)));
					const lines = [
						truncateToWidth(location, width, SOFT_TEXT("...")),
						truncateToWidth(left + padding + right, width, ""),
					];

					const extensionStatuses = footerData.getExtensionStatuses();
					if (extensionStatuses.size > 0) {
						const statusLine = Array.from(extensionStatuses.entries())
							.sort(([a], [b]) => a.localeCompare(b))
							.map(([, text]) => sanitizeStatusText(text))
							.join(" ");
						lines.push(truncateToWidth(statusLine, width, SOFT_TEXT("...")));
					}

					return lines;
				},
			};
		});
	});
}
