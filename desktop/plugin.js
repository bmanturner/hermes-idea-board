// Idea Board, desktop half: a page listing the ideas with a detail view, plus first-run setup.
// Follows DESIGN.md: host components and host theme variables only, Hermes-sized chrome, and one
// larger reading moment (the idea's title and the user's own words). Copy speaks as the user's agent.
// Talks to dashboard/plugin_api.py through ctx.rest; never sends a chat message itself.
import {
  Badge,
  Button,
  Codicon,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  EmptyState,
  Kbd,
  Loader,
  PALETTE_AREA,
  ROUTES_AREA,
  SegmentedControl,
  SIDEBAR_NAV_AREA,
  Textarea,
  host,
  useMutation,
  useQuery,
  useQueryClient
} from '@hermes/plugin-sdk'
import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'idea-board'
const PATH = '/idea-board'
const BOARD_KEY = [ID, 'board']
const MODEL_SETTINGS = '/settings?tab=config:model&aux=idea_board'
let api = null

// ---- design tokens (DESIGN.md) ---------------------------------------------------------------
// Colors are host variables only (The Borrowed Ink Rule).
const C = {
  p: 'var(--ui-text-primary)',
  s: 'var(--ui-text-secondary)',
  t: 'var(--ui-text-tertiary)',
  line: 'var(--ui-stroke-tertiary)',
  ring: 'var(--ui-stroke-secondary)',
  accent: 'var(--ui-accent)',
  alert: 'var(--ui-red)'
}
// The type roles (The Eight Roles Rule). `control` belongs to host Button, Badge and SegmentedControl.
const T = {
  overline: { fontSize: '0.6rem', fontWeight: 500, lineHeight: 1.5, letterSpacing: '0.05em', textTransform: 'uppercase' },
  meta: { fontSize: '0.7rem', fontWeight: 400, lineHeight: 1.5 },
  row: { fontSize: '0.78rem', fontWeight: 500, lineHeight: 1.5 },
  body: { fontSize: '0.8125rem', fontWeight: 400, lineHeight: 1.5 },
  title: { fontSize: '0.875rem', fontWeight: 600, lineHeight: 1.43 },
  quote: { fontSize: '0.9375rem', fontWeight: 400, lineHeight: 1.5, fontStyle: 'italic' },
  ideaTitle: { fontSize: '1.25rem', fontWeight: 600, lineHeight: 1.25, letterSpacing: '-0.01em', textWrap: 'balance' }
}
const PROSE = '68ch'
const NARROW = 760

// States that inline styles can't express: hover, focus, selection, and the narrow-window stack.
const STYLE = `
.ib-page { container: ib / inline-size; }
.ib-split { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 32px; flex: 1; min-height: 0; }
.ib-list-col { display: flex; flex-direction: column; gap: 16px; overflow: auto; min-height: 0; border-right: 1px solid var(--ui-stroke-tertiary); padding: 0 16px 24px 0; }
.ib-detail-col { display: flex; flex-direction: column; gap: 12px; overflow: auto; min-height: 0; padding-bottom: 32px; }
.ib-row { all: unset; box-sizing: border-box; display: flex; flex-direction: column; gap: 2px; padding: 6px 8px; border-radius: 2px; cursor: pointer; }
.ib-row:hover { background: var(--ui-row-hover-background); }
.ib-row.is-selected { background: var(--ui-row-active-background); }
.ib-row:focus-visible { outline: 2px solid var(--ui-accent); outline-offset: -2px; }
.ib-row[disabled] { cursor: default; }
.ib-row[disabled]:hover { background: transparent; }
.ib-step { flex-direction: row; align-items: flex-start; gap: 8px; }
.ib-mark { flex: none; box-sizing: border-box; width: 18px; height: 18px; margin-top: 1px; border-radius: 9999px; display: grid; place-items: center; font-size: 0.7rem; line-height: 1; color: var(--ui-text-tertiary); box-shadow: inset 0 0 0 1px var(--ui-stroke-secondary); }
.ib-mark.is-done { background: var(--ui-accent); color: var(--dt-primary-foreground); box-shadow: none; }
.ib-prompt { background: var(--ui-bg-quinary); color: var(--ui-text-secondary); border-radius: 4px; padding: 10px; font-size: 0.8125rem; line-height: 1.5; }
.ib-prompt-text { white-space: pre-wrap; overflow: hidden; }
.ib-prompt-text.is-clamped { display: -webkit-box; -webkit-line-clamp: 8; -webkit-box-orient: vertical; }
.ib-undo { display: flex; align-items: center; gap: 12px; background: var(--ui-bg-quaternary); color: var(--ui-text-secondary); border-radius: 4px; padding: 8px 12px; font-size: 0.8125rem; line-height: 1.5; max-width: 720px; }
@container ib (max-width: ${NARROW}px) {
  .ib-split { grid-template-columns: minmax(0, 1fr); gap: 16px; overflow: auto; }
  .ib-list-col { border-right: 0; border-bottom: 1px solid var(--ui-stroke-tertiary); padding: 0 0 16px; overflow: visible; }
  .ib-detail-col { overflow: visible; }
}
`

const KINDS = [
  { kind: 'recurring', label: 'Put on autopilot', icon: 'sync' },
  { kind: 'once', label: 'Do once', icon: 'zap' },
  { kind: 'connector', label: 'Connect next', icon: 'plug' }
]
const KIND = Object.fromEntries(KINDS.map(k => [k.kind, k]))
const CAP_ICON = { mcp: 'plug', skill: 'book', toolset: 'tools', platform: 'comment-discussion', connector: 'link' }
// What the agent promises before the user starts an idea. Shown beside the Start button.
const RISK = {
  none: 'I’ll show you a plan first, then only read and draft.',
  'drafts-for-approval': 'I’ll show you a plan first and prepare drafts for your OK.',
  'external-action': 'I’ll show you a plan first and act only after your yes.'
}
const sleep = ms => new Promise(r => setTimeout(r, ms))

// ---- data ------------------------------------------------------------------------------------
const rest = (path, opts) => api.rest(path, opts)

function useBoard() {
  return useQuery({ queryKey: BOARD_KEY, queryFn: () => rest('/board'), refetchInterval: 60000, retry: 1 })
}

async function placeInNewChat(text) {
  host.newChat()
  for (let i = 0; i < 30; i++) {
    if (await host.composer.setDraft('new', text)) {
      host.composer.focus('new')
      return true
    }
    await sleep(100)
  }
  return false
}

async function startIdea(card) {
  rest(`/cards/${card.id}/started`, { method: 'POST' }).catch(() => {})
  if (await placeInNewChat(card.prompt)) return
  const copied = await api.os.writeClipboard(card.prompt)
  host.notify({
    kind: copied ? 'info' : 'error',
    message: copied
      ? 'I couldn’t open a new chat, so the prompt is on your clipboard. Paste it and press send.'
      : 'I couldn’t open a new chat with this idea. Use Copy prompt instead.'
  })
}

async function generateNow() {
  const ok = await placeInNewChat('/idea-board generate')
  if (!ok) host.notify({ kind: 'error', message: 'I couldn’t open a new chat. Open one and send /idea-board generate.' })
}

const failed = what => e => {
  const detail = String((e && e.message) || e || '').slice(0, 80)
  host.notify({ kind: 'error', message: `I couldn’t ${what}${detail ? ` (${detail})` : ''}. Try again in a moment.` })
}

// ---- small pieces ----------------------------------------------------------------------------
const kids = list =>
  list
    .filter(c => c !== null && c !== undefined && c !== false && c !== '')
    .map((c, i) => (c && typeof c === 'object' && c.key != null ? c : jsx(Fragment, { children: c }, `k${i}`)))
const box = (base, style, children) => jsx('div', { style: { ...base, ...style }, children: Array.isArray(children) ? kids(children) : children })
const row = (style, children) => box({ display: 'flex', alignItems: 'center' }, style, children)
const col = (style, children) => box({ display: 'flex', flexDirection: 'column' }, style, children)
const txt = (role, color, children, style) => jsx('div', { style: { ...T[role], color, ...style }, children })
const icon = (name, style) => jsx(Codicon, { name, size: '1em', style })
const heading = (level, role, color, children, style) => jsx(`h${level}`, { style: { ...T[role], color, margin: 0, ...style }, children })

// "daily 21:30 America/Chicago" -> "daily at 9:30 PM" (the zone is dropped when it's the user's own).
function friendlySchedule(s) {
  const m = String(s || '').match(/^(.*?)\s*(?:at\s+)?(\d{1,2}):(\d{2})(?:\s+([A-Za-z_]+\/[A-Za-z_\/]+))?$/)
  if (!m) return s
  const [, days, hh, mm, zone] = m
  const t = new Date(2000, 0, 1, Number(hh), Number(mm)).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  let local = ''
  try {
    local = Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch {}
  return `${days ? `${days} at ` : ''}${t}${zone && zone !== local ? ` ${zone.replace(/_/g, ' ')}` : ''}`
}

function when(ts) {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' })
}

function shortDate(iso) {
  const [y, m, d] = String(iso).split('-').map(Number)
  if (!y || !m || !d) return String(iso)
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function lastDays(n) {
  const out = []
  const now = new Date()
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i)
    out.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`)
  }
  return out
}

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`
const tokensK = run => Math.round(((run.input_tokens || 0) + (run.output_tokens || 0)) / 1000)

// Signature: fourteen days, the ones you said it on filled in.
function DayRibbon({ days }) {
  const hit = new Set(days || [])
  return row(
    { gap: 3 },
    lastDays(14).map(d =>
      jsx('span', {
        'aria-hidden': true,
        style: {
          width: 6,
          height: 6,
          borderRadius: 9999,
          background: hit.has(d) ? C.accent : 'transparent',
          boxShadow: hit.has(d) ? 'none' : `inset 0 0 0 1px ${C.ring}`
        }
      }, d)
    )
  )
}

const Overline = ({ children, iconName, style }) =>
  row({ ...T.overline, gap: 6, color: C.t, ...style }, [iconName && icon(iconName), jsx('span', { children })])

function ScheduleStatus({ jobQuery, setup, onSchedule }) {
  // Say nothing rather than guess when the scheduled-jobs list can't be read.
  if (!jobQuery || !jobQuery.isSuccess) return null
  const job = jobQuery.data
  if (job) {
    const paused = job.enabled === false || job.state === 'paused'
    return jsx('span', { style: { color: C.s }, children: paused ? 'Nightly run paused' : `I run nightly at ${timeLabel(job.schedule)}` })
  }
  if (setup && setup.schedule === 'manual') return jsx('span', { style: { color: C.s }, children: 'I run when you ask' })
  return jsx(Button, { variant: 'textStrong', size: 'inline', onClick: onSchedule, children: 'Not scheduled · Schedule' })
}

function Receipt({ run, jobQuery, setup, onSchedule }) {
  const change = jsx(Button, { variant: 'textStrong', size: 'inline', onClick: () => host.navigate(MODEL_SETTINGS), children: 'Change model' }, 'm')
  const status = jsx(ScheduleStatus, { jobQuery, setup, onSchedule }, 'sched')
  if (!run) return row({ ...T.meta, gap: 12, flexWrap: 'wrap', color: C.t }, [status, jsx('span', { children: 'No run yet' })])
  if (run.status === 'error') {
    return row({ ...T.meta, gap: 12, flexWrap: 'wrap', color: C.t }, [
      status,
      jsx('span', { style: { color: C.alert }, children: `My last run, ${when(run.finished_at)}, failed: ${String(run.error || 'unknown error').slice(0, 120)}` }),
      change
    ])
  }
  const parts = [
    `Last run ${when(run.finished_at)}`,
    `I read ${plural(run.sessions_read, 'chat')} and kept ${run.kept} of ${plural(run.candidates, 'idea')}`,
    `${run.model || 'default model'} · ${tokensK(run)}k tokens`
  ]
  return row({ ...T.meta, gap: 12, flexWrap: 'wrap', color: C.t }, [status, ...parts.map(p => jsx('span', { children: p })), change])
}

function Caps({ uses }) {
  const seen = new Set()
  const unique = uses.filter(u => !seen.has(u.name.toLowerCase()) && seen.add(u.name.toLowerCase()))
  if (!unique.length) return null
  return row(
    { gap: 6, flexWrap: 'wrap' },
    unique.map(u => jsxs(Badge, { variant: 'muted', children: [icon(CAP_ICON[u.kind] || 'tools', { marginRight: 4 }), u.name] }, u.id))
  )
}

function Quote({ item }) {
  const friction = item.kind === 'tool_friction'
  return txt('quote', C.p, friction ? item.quote : `“${item.quote}”`, friction ? { fontStyle: 'normal' } : null)
}

function Evidence({ items: raw }) {
  const seen = new Set()
  const items = raw.filter(e => !seen.has(e.quote) && seen.add(e.quote))
  if (!items.length) return null
  return col(
    { gap: 12 },
    items.slice(0, 3).map(e =>
      col({ gap: 4 }, [
        jsx(Quote, { item: e }),
        row({ ...T.meta, gap: 8, color: C.t, flexWrap: 'wrap' }, [
          jsx(DayRibbon, { days: e.days }),
          jsx('span', { children: e.days.length > 1 ? `${e.days.length} days in the last two weeks` : 'once' }),
          ...chatLinks(e.session_ids)
        ])
      ])
    )
  )
}

function chatLinks(ids) {
  const list = (ids || []).slice(0, 3)
  return list.map((id, i) =>
    jsx(Button, {
      variant: 'textStrong',
      size: 'inline',
      onClick: () => host.openSession(id),
      children: list.length === 1 ? 'Open chat' : `Open chat ${i + 1}`
    }, `o${id}`)
  )
}

function MetaLine({ card }) {
  const k = KIND[card.kind] || KIND.once
  return row({ ...T.meta, gap: 6, color: C.t, flexWrap: 'wrap' }, [
    icon(k.icon),
    jsx('span', { children: k.label }),
    card.schedule && jsx('span', { children: `· ${friendlySchedule(card.schedule)}` }),
    jsx('span', { style: { color: C.s }, children: `· ${card.value_note}` }),
    card.expires && jsxs(Badge, { variant: 'muted', size: 'xs', title: 'Worth doing before this date', children: [icon('calendar', { marginRight: 4 }), `by ${shortDate(card.expires)}`] }, 'e'),
    card.stretch && jsx(Badge, { variant: 'muted', size: 'xs', title: 'An ambitious idea that chains several tools', children: 'Stretch' }, 'x')
  ])
}

function PromptPreview({ card }) {
  const [open, setOpen] = useState(false)
  const body = card.prompt
    .replace(/^\[Idea Board · [^\]]+\][^\n]*\n[^\n]*\n\n/, '')
    .replace(/\n\n— Idea Board · IB-\d+\s*$/, '')
  return col({ gap: 6, maxWidth: PROSE }, [
    jsx(Overline, { children: 'Your message · goes into a new chat' }),
    jsx('div', { className: 'ib-prompt', children: jsx('div', { className: open ? 'ib-prompt-text' : 'ib-prompt-text is-clamped', children: body }) }),
    row({ ...T.meta, gap: 12, color: C.t, flexWrap: 'wrap' }, [
      jsx(Button, { variant: 'text', size: 'inline', onClick: () => setOpen(!open), children: open ? 'Show less' : 'Show all' }, 't'),
      jsx(Button, {
        variant: 'text',
        size: 'inline',
        onClick: async () => {
          const ok = await api.os.writeClipboard(card.prompt)
          host.notify({ kind: ok ? 'info' : 'error', message: ok ? 'Prompt copied.' : 'I couldn’t copy the prompt.' })
        },
        children: 'Copy prompt'
      }, 'c')
    ])
  ])
}

// ---- dismiss -----------------------------------------------------------------------------------
function DismissMenu({ card, reasons, onDismiss, onNote }) {
  return jsxs(DropdownMenu, {
    children: [
      jsx(DropdownMenuTrigger, {
        asChild: true,
        children: jsxs(Button, { variant: 'ghost', children: ['Dismiss', icon('chevron-down', { marginLeft: 4 })] })
      }),
      jsxs(DropdownMenuContent, {
        align: 'start',
        children: [
          ...reasons
            .filter(r => r.code !== 'wrong_timing')
            .map(r => jsx(DropdownMenuItem, { onSelect: () => onDismiss(card, r.code, ''), children: r.label }, r.code)),
          jsx(DropdownMenuSeparator, {}, 'sep'),
          jsx(DropdownMenuItem, { onSelect: () => onNote(card), children: 'Dismiss with a note…' }, 'note')
        ]
      })
    ]
  })
}

function NoteDialog({ card, reasons, onClose, onDismiss }) {
  const [reason, setReason] = useState('not_relevant')
  const [note, setNote] = useState('')
  return jsx(Dialog, {
    open: Boolean(card),
    onOpenChange: o => !o && onClose(),
    children: jsxs(DialogContent, {
      children: [
        jsxs(DialogHeader, {
          children: [
            jsx(DialogTitle, { children: 'Why not this one?' }),
            jsx(DialogDescription, { children: 'Your reason becomes a rule I follow on every run. You can edit or delete it later.' })
          ]
        }),
        col({ gap: 12 }, [
          jsx('div', {
            role: 'radiogroup',
            'aria-label': 'Reason',
            style: { display: 'flex', flexDirection: 'column', gap: 2 },
            children: reasons
              .filter(r => r.code !== 'wrong_timing')
              .map(r =>
                jsxs('button', {
                  type: 'button',
                  role: 'radio',
                  'aria-checked': r.code === reason,
                  className: r.code === reason ? 'ib-row is-selected' : 'ib-row',
                  style: { flexDirection: 'row', alignItems: 'center', gap: 8, ...T.row, color: C.p },
                  onClick: () => setReason(r.code),
                  children: [
                    jsx('span', { style: { width: '1em', display: 'inline-flex', color: C.accent }, children: r.code === reason ? icon('check') : null }),
                    r.label
                  ]
                }, r.code)
              )
          }),
          jsx(Textarea, {
            value: note,
            onChange: e => setNote(e.target.value),
            placeholder: 'In your words (optional): what should I stop suggesting?',
            rows: 3
          })
        ]),
        jsxs(DialogFooter, {
          children: [
            jsx(Button, { variant: 'text', onClick: onClose, children: 'Cancel' }),
            jsx(Button, {
              onClick: () => {
                onDismiss(card, reason, note)
                onClose()
              },
              children: 'Dismiss'
            })
          ]
        })
      ]
    })
  })
}

// ---- rules -----------------------------------------------------------------------------------
function RulesDialog({ open, onClose, rules }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(null)
  const [confirming, setConfirming] = useState(null)
  const [draft, setDraft] = useState('')
  const save = useMutation({
    mutationFn: ({ id, text }) => rest(`/rules/${id}`, { method: 'PATCH', body: { text } }),
    onSuccess: () => {
      setEditing(null)
      qc.invalidateQueries({ queryKey: BOARD_KEY })
    },
    onError: failed('save the rule')
  })
  const remove = useMutation({
    mutationFn: id => rest(`/rules/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
    onError: failed('delete the rule')
  })
  return jsx(Dialog, {
    open,
    onOpenChange: o => !o && onClose(),
    children: jsxs(DialogContent, {
      children: [
        jsxs(DialogHeader, {
          children: [
            jsx(DialogTitle, { children: 'What I’ve learned' }),
            jsx(DialogDescription, { children: 'Rules from your dismissals. I follow them on every run.' })
          ]
        }),
        rules.length === 0
          ? txt('body', C.t, 'No rules yet. When you dismiss an idea, its reason becomes a rule here.', { padding: '8px 0' })
          : col(
              { maxHeight: 360, overflow: 'auto' },
              rules.map(r =>
                jsx(Fragment, {
                  children: col({ gap: 4, padding: '12px 0', borderTop: `1px solid ${C.line}` }, [
                    editing === r.id
                      ? jsx(Textarea, { value: draft, onChange: e => setDraft(e.target.value), rows: 2, autoFocus: true }, 'ta')
                      : txt('body', C.p, r.text),
                    confirming === r.id
                      ? row({ ...T.meta, gap: 12, color: C.t }, [
                          jsx('span', { children: 'Delete this rule? I may suggest these ideas again.' }),
                          jsx(Button, { variant: 'textStrong', size: 'inline', onClick: () => { setConfirming(null); remove.mutate(r.id) }, children: 'Delete' }, 'y'),
                          jsx(Button, { variant: 'text', size: 'inline', onClick: () => setConfirming(null), children: 'Keep' }, 'n')
                        ])
                      : row({ ...T.meta, gap: 12, color: C.t }, [
                          jsx('span', { children: r.hits ? `kept ${plural(r.hits, 'idea')} off the board` : 'not used yet' }),
                          editing === r.id
                            ? jsx(Button, { variant: 'textStrong', size: 'inline', onClick: () => save.mutate({ id: r.id, text: draft }), children: 'Save' }, 's')
                            : jsx(Button, { variant: 'text', size: 'inline', onClick: () => { setEditing(r.id); setDraft(r.text) }, children: 'Edit' }, 'e'),
                          jsx(Button, { variant: 'text', size: 'inline', onClick: () => setConfirming(r.id), children: 'Delete' }, 'd')
                        ])
                  ])
                }, r.id)
              )
            ),
        jsx(DialogFooter, { children: jsx(Button, { variant: 'secondary', onClick: onClose, children: 'Done' }) })
      ]
    })
  })
}

// ---- setup (onboarding) ----------------------------------------------------------------------
// Shown until the user finishes it. Nothing is scheduled until they press "Schedule it".
const JOB_NAME = 'Idea Board nightly'
const JOB_PROMPT = 'Call the idea_board_run tool once. Do nothing else, then reply [SILENT].'
const TIMES = [
  { id: '0 2 * * *', label: '2:00 AM' },
  { id: '30 3 * * *', label: '3:30 AM' },
  { id: '0 5 * * *', label: '5:00 AM' }
]
const timeLabel = cron => (TIMES.find(t => t.id === cron) || {}).label || cron
const profileName = () => {
  try {
    return host.state.profile.get() || undefined
  } catch {
    return undefined
  }
}

async function cronRequest(params) {
  return host.request('cron.manage', { ...params, profile: profileName() })
}

function useNightlyJob() {
  return useQuery({
    queryKey: [ID, 'job', profileName()],
    queryFn: async () => {
      const res = await cronRequest({ action: 'list', include_disabled: true })
      return (res.jobs || []).find(j => j.name === JOB_NAME) || null
    },
    retry: 0
  })
}

// Shown in step 1 so the first screen shows what the board makes instead of describing it.
const EXAMPLE_IDEA = {
  title: 'Put your weekly status update on autopilot',
  value_note: '≈ 1.5 h/month',
  evidence: [{ kind: 'repeat', quote: 'Can you draft my weekly status update again?', days: [] }]
}

function SampleIdea({ card, example }) {
  const ev = (card.evidence || []).find(e => e.kind !== 'tool_friction') || (card.evidence || [])[0]
  const days = example ? lastDays(14).filter((_, i) => i === 2 || i === 7 || i === 12) : ev && ev.days
  return col({ gap: 8, paddingTop: 16, borderTop: `1px solid ${C.line}` }, [
    jsx(Overline, { children: example ? 'Example · yours come from your own chats' : 'An idea from your chats' }),
    heading(3, 'ideaTitle', C.p, card.title),
    ev && jsx(Quote, { item: ev }),
    row({ ...T.meta, gap: 8, color: C.t, flexWrap: 'wrap' }, [
      ev && jsx(DayRibbon, { days }),
      jsx('span', { children: card.value_note }),
      ...(example || !ev ? [] : chatLinks(ev.session_ids))
    ])
  ])
}

function Field({ label, children }) {
  return row({ gap: 12, flexWrap: 'wrap' }, [txt('body', C.t, label, { width: 140, flex: 'none' }), children])
}

function StepRow({ n, title, value, done, selected, onSelect }) {
  return jsxs('button', {
    type: 'button',
    className: `ib-row ib-step${selected ? ' is-selected' : ''}`,
    'aria-current': selected ? 'step' : undefined,
    'aria-label': `Step ${n}, ${title}: ${value}${done ? ', done' : ''}`,
    onClick: onSelect,
    children: [
      jsx('span', { className: done ? 'ib-mark is-done' : 'ib-mark', 'aria-hidden': true, children: done ? icon('check') : n }),
      col({ gap: 2, minWidth: 0 }, [txt('row', C.p, title), txt('meta', C.t, value)])
    ]
  })
}

function SetupView({ data, onDone, initialStep }) {
  const qc = useQueryClient()
  const setup = data.setup
  const job = useNightlyJob()
  const [keepMain, setKeepMain] = useState(false)
  const [mode, setMode] = useState(setup.schedule === 'manual' ? 'manual' : 'nightly')
  const [time, setTime] = useState('30 3 * * *')
  const [firstAsked, setFirstAsked] = useState(false)
  const [reviewed, setReviewed] = useState(Boolean(setup.done))
  const save = useMutation({
    mutationFn: body => rest('/setup', { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
    onError: failed('save that')
  })
  const schedule = useMutation({
    mutationFn: async () => {
      const res = await cronRequest({ action: 'add', name: JOB_NAME, schedule: time, prompt: JOB_PROMPT, deliver: 'local' })
      if (res && res.error) throw new Error(res.error)
      return res
    },
    onSuccess: () => {
      save.mutate({ schedule: `nightly ${time}` })
      qc.invalidateQueries({ queryKey: [ID, 'job'] })
    },
    onError: failed('schedule the nightly run')
  })

  // Refresh the model line when the user comes back from Settings.
  useEffect(() => {
    const onFocus = () => qc.invalidateQueries({ queryKey: BOARD_KEY })
    window.addEventListener('focus', onFocus)
    const t = setInterval(onFocus, 5000)
    return () => {
      window.removeEventListener('focus', onFocus)
      clearInterval(t)
    }
  }, [qc])

  const model = setup.model || {}
  const nightly = job.data
  const cards = data.cards
  const hasIdeas = cards.length > 0
  const tokens = data.last_run ? tokensK(data.last_run) : null
  const done = {
    1: reviewed,
    2: !model.follows_main || keepMain || Boolean(setup.done),
    3: Boolean(nightly) || setup.schedule === 'manual',
    4: hasIdeas || firstAsked
  }
  const doneCount = Object.values(done).filter(Boolean).length
  const allDone = doneCount === 4
  const [step, setStep] = useState(() => initialStep || [1, 2, 3, 4].find(n => !done[n]) || 1)
  const next = () => {
    if (step === 1) setReviewed(true)
    if (step === 2 && model.follows_main) setKeepMain(true)
    setStep(Math.min(4, step + 1))
  }
  const finish = () => (setup.done ? onDone() : save.mutate({ done: true }, { onSuccess: onDone }))
  // The One Blue Rule: Finish turns blue only when the open step has no blue action of its own.
  const stepHasPrimary = (step === 3 && !nightly && mode === 'nightly') || (step === 4 && !hasIdeas && !firstAsked)
  const modelName = model.name || 'your main model'
  const costLine = `Each run makes two model calls${tokens ? `; your last run used about ${tokens}k tokens` : ''}.`

  const steps = [
    { n: 1, title: 'What I read', value: `Last ${setup.history_days} days · up to ${setup.max_cards} ideas a run` },
    { n: 2, title: 'Which model I use', value: model.follows_main ? `${modelName} (your main model)` : `${model.name}, chosen for Idea Board` },
    {
      n: 3,
      title: 'When I run',
      value: nightly ? `Every night at ${timeLabel(nightly.schedule)}` : setup.schedule === 'manual' ? 'Only when you ask' : 'Not scheduled yet'
    },
    { n: 4, title: 'Your first ideas', value: hasIdeas ? `${plural(cards.length, 'idea')} waiting` : firstAsked ? 'Asked; they land here soon' : 'Not made yet' }
  ]

  const detail = {
    1: [
      txt('body', C.s, 'I read your own messages from recent chats (not scheduled jobs, subagents or group chats), plus the tools, skills, connected apps and scheduled jobs this profile has. Your ideas, dismissals and rules stay in this profile’s plugin data.', { maxWidth: PROSE }),
      col({ gap: 8, paddingTop: 4 }, [
        jsx(Field, {
          label: 'Chats to read',
          children: jsx(SegmentedControl, {
            value: String(setup.history_days),
            sizing: 'content',
            options: [{ id: '7', label: 'Last 7 days' }, { id: '14', label: 'Last 14 days' }, { id: '30', label: 'Last 30 days' }],
            onChange: v => { setReviewed(true); save.mutate({ history_days: Number(v) }) }
          })
        }),
        jsx(Field, {
          label: 'New ideas per run',
          children: jsx(SegmentedControl, {
            value: String(setup.max_cards),
            sizing: 'content',
            options: [{ id: '3', label: 'Up to 3' }, { id: '6', label: 'Up to 6' }, { id: '10', label: 'Up to 10' }],
            onChange: v => { setReviewed(true); save.mutate({ max_cards: Number(v) }) }
          })
        })
      ])
    ],
    2: [
      txt('body', C.s,
        model.follows_main
          ? `I’m using ${modelName}, your main model. ${costLine} A smaller model is usually enough.`
          : `I’m using ${model.name}, chosen for Idea Board. ${costLine}`,
        { maxWidth: PROSE }),
      row({ gap: 8, flexWrap: 'wrap' }, [
        jsx(Button, { variant: 'secondary', onClick: () => host.navigate(MODEL_SETTINGS), children: model.follows_main ? 'Choose a model for Idea Board' : 'Change model' }, 'c'),
        model.follows_main && !keepMain && jsx(Button, { variant: 'text', onClick: () => setKeepMain(true), children: 'Keep my main model' }, 'k')
      ])
    ],
    3: nightly
      ? [
          txt('body', C.s, `I run every night at ${timeLabel(nightly.schedule)}${nightly.state && nightly.state !== 'scheduled' ? ` (${nightly.state})` : ''}. I work quietly and post nothing; new ideas appear here.`, { maxWidth: PROSE }),
          row({}, [jsx(Button, { variant: 'textStrong', size: 'inline', onClick: () => api.runAction('nav.cron'), children: 'Pause or remove it on Scheduled jobs' }, 'j')])
        ]
      : [
          jsx(Field, {
            label: 'Run',
            children: jsx(SegmentedControl, {
              value: mode,
              sizing: 'content',
              options: [{ id: 'nightly', label: 'Every night' }, { id: 'manual', label: 'Only when you ask' }],
              onChange: v => {
                setMode(v)
                save.mutate({ schedule: v === 'manual' ? 'manual' : '' })
              }
            })
          }),
          mode === 'nightly' && jsx(Field, { label: 'Time', children: jsx(SegmentedControl, { value: time, sizing: 'content', options: TIMES, onChange: setTime }) }),
          txt('body', C.s,
            mode === 'nightly'
              ? 'I’ll add a scheduled job to this profile. Each night I read, think and save ideas here. I never message you or act on anything.'
              : 'I’ll make ideas only when you ask: from this page, or when you send /idea-board generate in any chat.',
            { maxWidth: PROSE, paddingTop: 4 }),
          mode === 'nightly' &&
            row({}, [jsx(Button, { disabled: schedule.isPending, onClick: () => schedule.mutate(), children: schedule.isPending ? 'Scheduling…' : `Schedule it for ${timeLabel(time)}` }, 's')])
        ],
    4: hasIdeas
      ? [txt('body', C.s, `You already have ${plural(cards.length, 'idea')} waiting. Finish setup to see them.`, { maxWidth: PROSE })]
      : firstAsked
        ? [
            txt('body', C.s, 'I opened a chat with /idea-board generate ready. Press send there, and ideas land here in a minute or two.', { maxWidth: PROSE }),
            row({}, [jsx(Button, { variant: 'secondary', onClick: generateNow, children: 'Open that chat again' }, 'g')])
          ]
        : [
            txt('body', C.s, 'I’ll open a new chat with /idea-board generate ready. Press send there, and ideas land here in a minute or two.', { maxWidth: PROSE }),
            row({}, [jsx(Button, { onClick: () => { setFirstAsked(true); generateNow() }, children: 'Open a chat to make ideas' }, 'g')])
          ]
  }[step]

  return jsxs('div', {
    className: 'ib-split',
    children: [
      jsx('div', {
        className: 'ib-list-col',
        children: kids([
          col({ gap: 2 }, [
            jsx(Overline, { style: { paddingBottom: 4 }, children: `Setup · ${doneCount} of 4 done` }),
            ...steps.map(s => jsx(StepRow, { ...s, done: done[s.n], selected: s.n === step, onSelect: () => setStep(s.n) }, s.n))
          ]),
          col({ gap: 8, alignItems: 'flex-start' }, [
            jsx(Button, {
              variant: allDone && !setup.done && !stepHasPrimary ? 'default' : 'secondary',
              disabled: save.isPending,
              onClick: finish,
              children: setup.done ? 'Back to my ideas' : hasIdeas ? 'Finish and show my ideas' : 'Finish setup'
            }),
            txt('meta', C.t, setup.done ? 'Changes save as you make them.' : !done[3] ? 'Nothing runs on its own until you schedule it.' : 'You can change any of this later from Setup.')
          ])
        ])
      }),
      jsx('div', {
        className: 'ib-detail-col',
        children: kids([
          col({ gap: 12, maxWidth: 720 }, [
            col({ gap: 2 }, [jsx(Overline, { children: `Step ${step} of 4` }), heading(2, 'title', C.p, steps[step - 1].title)]),
            ...detail,
            step < 4 &&
              row({ paddingTop: 4 }, [
                jsx(Button, { variant: step === 3 && !done[3] && mode === 'nightly' ? 'text' : 'secondary', onClick: next, children: step === 3 && !done[3] && mode === 'nightly' ? 'Skip for now' : 'Next' }, 'n')
              ])
          ]),
          step === 1 && col({ maxWidth: 720, paddingTop: 12 }, [jsx(SampleIdea, { card: hasIdeas ? cards[0] : EXAMPLE_IDEA, example: !hasIdeas })])
        ])
      })
    ]
  })
}

// ---- page --------------------------------------------------------------------------------------
function ListRow({ card, selected, onSelect }) {
  return jsxs('button', {
    type: 'button',
    className: selected ? 'ib-row is-selected' : 'ib-row',
    'data-card': card.id,
    'aria-current': selected ? 'true' : undefined,
    onClick: onSelect,
    children: [txt('row', C.p, card.title), txt('meta', C.t, card.value_note)]
  })
}

function Detail({ card, reasons, onStart, onSnooze, onDismiss, onNote }) {
  return col({ gap: 16, maxWidth: 720 }, [
    col({ gap: 8 }, [heading(2, 'ideaTitle', C.p, card.title), jsx(MetaLine, { card })]),
    txt('body', C.s, card.why, { maxWidth: PROSE }),
    jsx(Evidence, { items: card.evidence }),
    jsx(Caps, { uses: card.uses }),
    jsx(PromptPreview, { card }),
    col({ gap: 6, paddingTop: 8 }, [
      row({ gap: 8, flexWrap: 'wrap' }, [
        jsxs(Button, { onClick: () => onStart(card), children: [icon('comment', { marginRight: 6 }), 'Start in a new chat'] }, 's'),
        jsx(Button, { variant: 'secondary', onClick: () => onSnooze(card), children: 'Not now' }, 'n'),
        jsx(DismissMenu, { card, reasons, onDismiss, onNote }, 'd')
      ]),
      txt('meta', C.t, `You read it and press send. ${RISK[card.risk] || RISK.none}`)
    ]),
    row({ ...T.meta, gap: 12, color: C.t, flexWrap: 'wrap' }, [
      jsxs('span', { children: [jsx(Kbd, { children: '↑' }), ' ', jsx(Kbd, { children: '↓' }), ' move'] }),
      jsxs('span', { children: [jsx(Kbd, { children: 'Enter' }), ' start'] }),
      jsxs('span', { children: [jsx(Kbd, { children: 'N' }), ' not now'] }),
      jsxs('span', { children: [jsx(Kbd, { children: 'D' }), ' dismiss'] })
    ])
  ])
}

function Started({ cards }) {
  if (!cards.length) return null
  return col({ gap: 2 }, [
    jsx(Overline, { style: { paddingBottom: 4 }, children: `Started · ${cards.length}` }),
    ...cards.slice(0, 5).map(c =>
      jsxs('button', {
        type: 'button',
        className: 'ib-row',
        disabled: !c.session_id,
        title: c.session_id ? 'Open the chat' : undefined,
        onClick: () => c.session_id && host.openSession(c.session_id),
        style: { flexDirection: 'row', alignItems: 'center', gap: 6, ...T.meta, color: C.t },
        children: [
          icon(c.outcome === 'done' ? 'check' : 'comment'),
          jsx('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: c.title })
        ]
      }, c.id)
    )
  ])
}

function Empty({ title, description, extra, action }) {
  return col({ flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16, paddingBottom: 80 }, [
    jsx(EmptyState, { title, description, className: 'min-h-0' }),
    extra,
    action
  ])
}

const code = text =>
  jsx('code', {
    style: { ...T.meta, fontFamily: 'var(--font-mono)', padding: '1px 4px', borderRadius: 2, background: 'var(--ui-inline-code-background)', color: 'var(--ui-inline-code-foreground)' },
    children: text
  })

function Header({ data, jobQuery, inSetup, onRules, onSetup, onSchedule }) {
  const setupDone = Boolean(data && data.setup && data.setup.done)
  return row({ justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, paddingBottom: 12, borderBottom: `1px solid ${C.line}`, flexWrap: 'wrap' }, [
    col({ gap: 4, minWidth: 0, flex: '1 1 320px' }, [
      jsx('h1', { style: { ...T.title, color: C.p, margin: 0 }, children: 'Idea Board' }),
      inSetup
        ? txt('meta', C.t, setupDone ? 'Setup' : 'Setup · about two minutes · I only run once you schedule me or ask')
        : data && jsx(Receipt, { run: data.last_run, jobQuery, setup: data.setup, onSchedule })
    ]),
    setupDone && !inSetup &&
      row({ gap: 8, marginLeft: 'auto' }, [
        jsx(Button, { variant: 'text', onClick: onSetup, children: 'Setup' }, 'setup'),
        jsx(Button, { variant: 'secondary', onClick: onRules, children: `What I’ve learned (${data.rules.length})` }, 'rules')
      ])
  ])
}

function BoardPage() {
  const qc = useQueryClient()
  const board = useBoard()
  const [selected, setSelected] = useState(null)
  const [noteFor, setNoteFor] = useState(null)
  const [rulesOpen, setRulesOpen] = useState(false)
  const [undo, setUndo] = useState(null)
  const [showSetup, setShowSetup] = useState(false)
  const [setupStep, setSetupStep] = useState(null)
  const job = useNightlyJob()
  const rootRef = useRef(null)
  const detailRef = useRef(null)
  const data = board.data
  const cards = data ? data.cards : []
  const ordered = useMemo(() => KINDS.flatMap(k => cards.filter(c => c.kind === k.kind)), [cards])
  const current = ordered.find(c => c.id === selected) || ordered[0]
  const inSetup = Boolean(data && data.setup && (!data.setup.done || showSetup))

  useEffect(() => {
    rootRef.current && rootRef.current.focus({ preventScroll: true })
  }, [])

  const refresh = () => qc.invalidateQueries({ queryKey: BOARD_KEY })
  const focusRow = id =>
    setTimeout(() => {
      const root = rootRef.current
      const b = root && id && root.querySelector(`[data-card="${id}"]`)
      if (b) b.focus()
      else if (root) root.focus({ preventScroll: true })
    }, 60)
  const select = (id, { focus = false } = {}) => {
    if (id !== selected) setUndo(null)
    setSelected(id)
    const root = rootRef.current
    if (!root) return
    if (focus) {
      focusRow(id)
    } else if (root.clientWidth - 64 <= NARROW && detailRef.current) {
      // Stacked layout: bring the detail into view after picking from the list.
      requestAnimationFrame(() => detailRef.current && detailRef.current.scrollIntoView({ block: 'start' }))
    }
  }
  const nextAfter = card => {
    const i = ordered.findIndex(c => c.id === card.id)
    const next = ordered[i + 1] || ordered[i - 1]
    setSelected(next ? next.id : null)
    // Keep the keyboard flow going: focus moves to the idea that took this one's place.
    focusRow(next && next.id)
  }
  const dismiss = useMutation({
    mutationFn: ({ card, reason, note }) => rest(`/cards/${card.id}/dismiss`, { method: 'POST', body: { reason, note } }),
    onMutate: ({ card }) => nextAfter(card),
    onSuccess: (res, { card }) => {
      setUndo({
        card,
        rule: Boolean(res.rule),
        message: res.rule ? `Dismissed. ${res.rule}` : res.action === 'evidence_consumed' ? 'Dismissed. I’ll count that as handled.' : 'Dismissed.'
      })
      refresh()
    },
    onError: failed('dismiss it')
  })
  const snooze = useMutation({
    mutationFn: card => rest(`/cards/${card.id}/snooze`, { method: 'POST', body: { days: 7 } }),
    onMutate: card => nextAfter(card),
    onSuccess: (_r, card) => {
      setUndo({ card, message: 'I’ll hide it for a week.' })
      refresh()
    },
    onError: failed('hide it')
  })
  const undoMut = useMutation({
    mutationFn: card => rest(`/cards/${card.id}/undo`, { method: 'POST' }),
    onSuccess: (_r, card) => {
      setUndo(null)
      setSelected(card.id)
      refresh()
    },
    onError: failed('undo that')
  })
  const start = card => {
    setUndo(null)
    startIdea(card).finally(refresh)
  }
  const onDismiss = (card, reason, note) => dismiss.mutate({ card, reason, note })

  const onKeyDown = e => {
    if (inSetup || !current || e.metaKey || e.ctrlKey || e.altKey) return
    const t = e.target
    // Keys work anywhere on the page except text fields and anything rendered outside it (dialogs, menus).
    if (!rootRef.current || !rootRef.current.contains(t) || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable) return
    const onRow = Boolean(t.closest && t.closest('[data-card]'))
    const k = e.key.length === 1 ? e.key.toLowerCase() : e.key
    const i = ordered.findIndex(c => c.id === current.id)
    if (k === 'ArrowDown' || k === 'ArrowUp') {
      e.preventDefault()
      const n = ordered[Math.max(0, Math.min(ordered.length - 1, i + (k === 'ArrowDown' ? 1 : -1)))]
      n && select(n.id, { focus: onRow })
    } else if ((k === 'Enter' && (onRow || t === rootRef.current)) || k === 's') {
      e.preventDefault()
      start(current)
    } else if (k === 'n') {
      e.preventDefault()
      snooze.mutate(current)
    } else if (k === 'd') {
      e.preventDefault()
      setNoteFor(current)
    }
  }
  const openSetup = step => {
    setSetupStep(step || null)
    setShowSetup(true)
  }

  let body
  if (board.isLoading) {
    body = row({ flex: 1, justifyContent: 'center' }, jsx(Loader, {}))
  } else if (board.isError) {
    body = jsx(Empty, {
      title: 'Idea Board isn’t on for this profile',
      description: 'Turn it on in Settings → Plugins. If it’s on and you still see this, enable its backend, then restart Hermes:',
      extra: code('hermes plugins enable idea-board'),
      action: jsx(Button, { variant: 'secondary', onClick: () => host.navigate('/settings/plugins'), children: 'Open Plugins' })
    })
  } else if (inSetup) {
    body = jsx(SetupView, { data, initialStep: setupStep, onDone: () => setShowSetup(false) }, setupStep || 'setup')
  } else if (!cards.length) {
    const next = job.data ? `I’ll look again tonight at ${timeLabel(job.data.schedule)}.` : 'Ask me to look again whenever you like.'
    body = jsx(Empty, {
      title: data.last_run ? 'No new ideas right now' : 'No ideas yet',
      description: data.last_run
        ? `Last run, I found nothing worth your time that you haven’t already seen. ${next}`
        : 'I read your recent chats and what this profile can do, then suggest things I could take off your plate.',
      extra: txt('meta', C.t, 'This opens a new chat with /idea-board generate ready; press send there.'),
      action: jsx(Button, { onClick: generateNow, children: data.last_run ? 'Look again in a new chat' : 'Make ideas in a new chat' })
    })
  } else {
    body = jsxs('div', {
      className: 'ib-split',
      children: [
        jsx('div', {
          className: 'ib-list-col',
          children: kids([
            ...KINDS.map(k => {
              const items = ordered.filter(c => c.kind === k.kind)
              if (!items.length) return null
              return col({ gap: 2 }, [
                jsx(Overline, { iconName: k.icon, style: { paddingBottom: 4 }, children: `${k.label} · ${items.length}` }),
                ...items.map(c => jsx(ListRow, { card: c, selected: current && c.id === current.id, onSelect: () => select(c.id) }, c.id))
              ])
            }),
            jsx(Started, { cards: data.started }, 'started')
          ])
        }),
        jsx('div', {
          className: 'ib-detail-col',
          ref: detailRef,
          children: kids([
            undo &&
              jsx('div', {
                className: 'ib-undo',
                role: 'status',
                children: kids([
                  jsx('span', { style: { flex: 1 }, children: undo.message }),
                  undo.rule && jsx(Button, { variant: 'text', size: 'inline', onClick: () => setRulesOpen(true), children: 'Edit rules' }, 'r'),
                  jsx(Button, { variant: 'textStrong', size: 'inline', onClick: () => undoMut.mutate(undo.card), children: 'Undo' }, 'u')
                ])
              }),
            current && jsx(Detail, { card: current, reasons: data.reasons, onStart: start, onSnooze: c => snooze.mutate(c), onDismiss, onNote: setNoteFor })
          ])
        })
      ]
    })
  }

  return jsxs('div', {
    ref: rootRef,
    tabIndex: 0,
    onKeyDown,
    className: 'ib-page',
    style: { height: '100%', boxSizing: 'border-box', display: 'flex', flexDirection: 'column', padding: '24px 32px 0', gap: 16, minHeight: 0, outline: 'none' },
    children: [
      jsx('style', { children: STYLE }),
      jsx(Header, { data, jobQuery: job, inSetup, onRules: () => setRulesOpen(true), onSetup: () => openSetup(), onSchedule: () => openSetup(3) }),
      jsx('div', { style: { flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }, children: body }),
      data && jsx(NoteDialog, { card: noteFor, reasons: data.reasons, onClose: () => setNoteFor(null), onDismiss }, noteFor ? noteFor.id : 'none'),
      data && jsx(RulesDialog, { open: rulesOpen, onClose: () => setRulesOpen(false), rules: data.rules })
    ]
  })
}

export default {
  id: ID,
  name: 'Idea Board',
  register(ctx) {
    api = ctx
    ctx.registerMany([
      { id: 'route', area: ROUTES_AREA, data: { path: PATH }, render: () => jsx(BoardPage, {}) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: PATH, label: 'Idea Board', codicon: 'lightbulb' } },
      {
        id: 'open',
        area: PALETTE_AREA,
        data: { id: 'idea-board.open', label: 'Open Idea Board', keywords: ['ideas', 'suggestions', 'offers'], run: () => host.navigate(PATH) }
      },
      {
        id: 'generate',
        area: PALETTE_AREA,
        data: { id: 'idea-board.generate', label: 'Idea Board: generate ideas now', keywords: ['ideas'], run: generateNow }
      }
    ])
  }
}
