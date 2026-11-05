// Idea Board, desktop half: a page listing tonight's ideas with a detail view.
// Uses only the app's own components and theme variables, so it follows every theme and skin.
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
import { useEffect, useMemo, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'idea-board'
const PATH = '/idea-board'
const BOARD_KEY = [ID, 'board']
let api = null

const C = {
  p: 'var(--ui-text-primary)',
  s: 'var(--ui-text-secondary)',
  t: 'var(--ui-text-tertiary)',
  q: 'var(--ui-text-quaternary)',
  line: 'var(--ui-stroke-tertiary)',
  soft: 'var(--ui-bg-quaternary)',
  accent: 'var(--ui-accent)'
}
const KINDS = [
  { kind: 'recurring', label: 'Put on autopilot', icon: 'sync' },
  { kind: 'once', label: 'Do once', icon: 'zap' },
  { kind: 'connector', label: 'Connect next', icon: 'plug' }
]
const KIND = Object.fromEntries(KINDS.map(k => [k.kind, k]))
const CAP_ICON = { mcp: 'plug', skill: 'book', toolset: 'tools', platform: 'comment-discussion', connector: 'link' }
const RISK = {
  none: 'Reads and drafts only',
  'drafts-for-approval': 'Prepares a draft for your OK',
  'external-action': 'Acts only after your yes'
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
      ? "Couldn't place the idea in a new chat, so it's on your clipboard. Paste it and press send."
      : "Couldn't open a new chat with this idea. Use Copy prompt in the detail view."
  })
}

// ---- small pieces ----------------------------------------------------------------------------
const row = (style, children) => jsx('div', { style: { display: 'flex', alignItems: 'center', ...style }, children })
const col = (style, children) => jsx('div', { style: { display: 'flex', flexDirection: 'column', ...style }, children })
const txt = (size, color, children, style) =>
  jsx('div', { style: { fontSize: size, color, lineHeight: 1.45, ...style }, children })

function when(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return d.toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' })
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

// Signature: fourteen days, the ones you said it on filled in.
function DayRibbon({ days }) {
  const hit = new Set(days || [])
  return row(
    { gap: 3 },
    lastDays(14).map(d =>
      jsx('span', {
        key: d,
        'aria-hidden': true,
        style: {
          width: 6,
          height: 6,
          borderRadius: 3,
          background: hit.has(d) ? C.accent : 'transparent',
          boxShadow: hit.has(d) ? 'none' : `inset 0 0 0 1px ${C.line}`
        }
      })
    )
  )
}

function Receipt({ run }) {
  if (!run) return txt(12, C.t, 'No run yet.')
  const tokens = Math.round(((run.input_tokens || 0) + (run.output_tokens || 0)) / 1000)
  const parts =
    run.status === 'error'
      ? [`Last run ${when(run.finished_at)} failed: ${run.error || 'unknown error'}`]
      : [
          `Last run ${when(run.finished_at)}`,
          `read ${run.sessions_read} chats`,
          `${run.evidence} signals`,
          `${run.candidates} drafted, ${run.kept} kept`,
          `${run.model || 'default model'} · ${tokens}k tokens`
        ]
  return row({ gap: 14, flexWrap: 'wrap', fontSize: 12, color: run.status === 'error' ? 'var(--ui-text-danger, ' + C.s + ')' : C.t }, [
    ...parts.map((p, i) => jsx('span', { children: p }, i)),
    jsx(Button, {
      variant: 'textStrong',
      size: 'inline',
      onClick: () => api.runAction('nav.settings'),
      children: 'Choose a model'
    }, 'm')
  ])
}

function Caps({ uses }) {
  const seen = new Set()
  const unique = uses.filter(u => !seen.has(u.name.toLowerCase()) && seen.add(u.name.toLowerCase()))
  return row(
    { gap: 6, flexWrap: 'wrap' },
    unique.map(u =>
      jsxs(Badge, {
        variant: 'muted',
        children: [jsx(Codicon, { name: CAP_ICON[u.kind] || 'tools', style: { marginRight: 4 } }), u.name]
      }, u.id)
    )
  )
}

function Evidence({ items: raw }) {
  const seen = new Set()
  const items = raw.filter(e => !seen.has(e.quote) && seen.add(e.quote))
  if (!items.length) return null
  return col(
    { gap: 12 },
    items.slice(0, 3).map((e, i) =>
      col({ gap: 5 }, [
        txt(14, C.s, e.kind === 'tool_friction' ? e.quote : `“${e.quote}”`, { fontStyle: e.kind === 'tool_friction' ? 'normal' : 'italic' }),
        row({ gap: 10, fontSize: 11.5, color: C.t, flexWrap: 'wrap' }, [
          jsx(DayRibbon, { days: e.days }, 'r'),
          jsx('span', { children: e.days.length > 1 ? `${e.days.length} days in the last two weeks` : 'once' }, 'n'),
          e.session_ids[0] &&
            jsx(Button, {
              variant: 'textStrong',
              size: 'inline',
              onClick: () => host.openSession(e.session_ids[0]),
              children: e.session_ids.length > 1 ? `Open chat (1 of ${e.session_ids.length})` : 'Open chat'
            }, 'o')
        ])
      ].map((c, j) => jsx('div', { children: c }, j)))
    ).map((c, i) => jsx('div', { children: c }, i))
  )
}

function MetaLine({ card }) {
  const k = KIND[card.kind] || KIND.once
  return row({ gap: 8, fontSize: 12, color: C.t, flexWrap: 'wrap' }, [
    jsx(Codicon, { name: k.icon }, 'i'),
    jsx('span', { children: k.label }, 'k'),
    card.schedule && jsx('span', { children: `· ${card.schedule}` }, 's'),
    jsx('span', { style: { color: C.s }, children: `· ${card.value_note}` }, 'v'),
    card.expires && jsx(Badge, { variant: 'warn', size: 'xs', children: `by ${shortDate(card.expires)}` }, 'e'),
    card.stretch && jsx(Badge, { variant: 'default', size: 'xs', children: 'Stretch' }, 'x')
  ])
}

function PromptPreview({ card }) {
  const [open, setOpen] = useState(false)
  const body = card.prompt
    .replace(/^\[Idea Board · [^\]]+\][^\n]*\n[^\n]*\n\n/, '')
    .replace(/\n\n— Idea Board · IB-\d+\s*$/, '')
  return col({ gap: 8, borderLeft: `1px solid ${C.line}`, paddingLeft: 14 }, [
    txt(11.5, C.t, 'Goes into a new chat. You read it and press send.', null),
    jsx('div', {
      style: {
        fontSize: 12.5,
        color: C.s,
        lineHeight: 1.55,
        whiteSpace: 'pre-wrap',
        overflow: 'hidden',
        ...(open ? {} : { display: '-webkit-box', WebkitLineClamp: 8, WebkitBoxOrient: 'vertical' })
      },
      children: body
    }),
    row({ gap: 12, fontSize: 11.5, color: C.q, flexWrap: 'wrap' }, [
      jsx('span', { children: `${RISK[card.risk] || RISK.none} · asks for a plan first` }, 'r'),
      jsx(Button, { variant: 'text', size: 'inline', onClick: () => setOpen(!open), children: open ? 'Show less' : 'Show all' }, 't'),
      jsx(Button, {
        variant: 'text',
        size: 'inline',
        onClick: async () => {
          const ok = await api.os.writeClipboard(card.prompt)
          host.notify({ kind: ok ? 'info' : 'error', message: ok ? 'Prompt copied.' : "Couldn't copy the prompt." })
        },
        children: 'Copy prompt'
      }, 'c')
    ])
  ].map((c, i) => jsx('div', { children: c }, i)))
}

// ---- dismiss -----------------------------------------------------------------------------------
function DismissMenu({ card, reasons, onDismiss, onNote }) {
  return jsxs(DropdownMenu, {
    children: [
      jsx(DropdownMenuTrigger, {
        asChild: true,
        children: jsxs(Button, { variant: 'ghost', children: ['Dismiss', jsx(Codicon, { name: 'chevron-down', style: { marginLeft: 4 } })] })
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
            jsx(DialogDescription, { children: 'Your reason becomes a rule the next runs follow. You can edit or delete it later.' })
          ]
        }),
        col({ gap: 10 }, [
          row(
            { gap: 6, flexWrap: 'wrap' },
            reasons
              .filter(r => r.code !== 'wrong_timing')
              .map(r =>
                jsx(Button, {
                  variant: r.code === reason ? 'default' : 'secondary',
                  size: 'sm',
                  onClick: () => setReason(r.code),
                  children: r.label
                }, r.code)
              )
          ),
          jsx(Textarea, {
            value: note,
            onChange: e => setNote(e.target.value),
            placeholder: 'In your words (optional): what should Idea Board stop suggesting?',
            rows: 3
          })
        ].map((c, i) => jsx('div', { children: c }, i))),
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
  const [draft, setDraft] = useState('')
  const save = useMutation({
    mutationFn: ({ id, text }) => rest(`/rules/${id}`, { method: 'PATCH', body: { text } }),
    onSuccess: () => {
      setEditing(null)
      qc.invalidateQueries({ queryKey: BOARD_KEY })
    },
    onError: e => host.notify({ kind: 'error', message: `Couldn't save the rule: ${e.message || e}` })
  })
  const remove = useMutation({
    mutationFn: id => rest(`/rules/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
    onError: e => host.notify({ kind: 'error', message: `Couldn't delete the rule: ${e.message || e}` })
  })
  return jsx(Dialog, {
    open,
    onOpenChange: o => !o && onClose(),
    children: jsxs(DialogContent, {
      children: [
        jsxs(DialogHeader, {
          children: [
            jsx(DialogTitle, { children: "What I've learned" }),
            jsx(DialogDescription, { children: 'Rules from your dismissals. Every run follows them.' })
          ]
        }),
        rules.length === 0
          ? txt(13, C.t, 'No rules yet. When you dismiss an idea, the reason shows up here.', { padding: '8px 0' })
          : col(
              { gap: 0, maxHeight: 360, overflow: 'auto' },
              rules.map(r =>
                col({ gap: 6, padding: '10px 0', borderTop: `1px solid ${C.line}` }, [
                  editing === r.id
                    ? jsx(Textarea, { value: draft, onChange: e => setDraft(e.target.value), rows: 2, autoFocus: true }, 'ta')
                    : txt(13.5, C.p, r.text, null),
                  row({ gap: 10, fontSize: 11.5, color: C.t }, [
                    jsx('span', { children: r.hits ? `kept out ${r.hits} idea${r.hits === 1 ? '' : 's'}` : 'not used yet' }, 'h'),
                    editing === r.id
                      ? jsx(Button, { variant: 'textStrong', size: 'inline', onClick: () => save.mutate({ id: r.id, text: draft }), children: 'Save' }, 's')
                      : jsx(Button, { variant: 'text', size: 'inline', onClick: () => { setEditing(r.id); setDraft(r.text) }, children: 'Edit' }, 'e'),
                    jsx(Button, { variant: 'text', size: 'inline', onClick: () => remove.mutate(r.id), children: 'Delete' }, 'd')
                  ])
                ].map((c, i) => jsx('div', { children: c }, i)))
              ).map((c, i) => jsx('div', { children: c }, rules[i].id))
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

function Step({ n, done, title, children }) {
  return jsxs('section', {
    style: { display: 'grid', gridTemplateColumns: '28px minmax(0, 1fr)', gap: 12, padding: '18px 0', borderTop: `1px solid ${C.line}` },
    children: [
      jsx('div', {
        'aria-hidden': true,
        style: {
          width: 22, height: 22, borderRadius: 11, display: 'grid', placeItems: 'center', fontSize: 11.5,
          color: done ? 'var(--ui-bg-editor, transparent)' : C.t,
          background: done ? C.accent : 'transparent',
          boxShadow: done ? 'none' : `inset 0 0 0 1px ${C.line}`
        },
        children: done ? jsx(Codicon, { name: 'check' }) : n
      }),
      col({ gap: 10, minWidth: 0 }, [txt(15, C.p, title, { fontWeight: 600 }), ...children].map((c, i) => jsx('div', { children: c }, i)))
    ]
  })
}

function Field({ label, children }) {
  return row({ gap: 12, flexWrap: 'wrap' }, [txt(13, C.s, label, { minWidth: 150 }), children].map((c, i) => jsx('div', { children: c }, i)))
}

function SetupView({ data, onDone }) {
  const qc = useQueryClient()
  const setup = data.setup
  const job = useNightlyJob()
  const [keepMain, setKeepMain] = useState(false)
  const [mode, setMode] = useState(setup.schedule === 'manual' ? 'manual' : 'nightly')
  const [time, setTime] = useState('30 3 * * *')
  const [firstAsked, setFirstAsked] = useState(false)
  const [reviewed, setReviewed] = useState(false)
  const save = useMutation({
    mutationFn: body => rest('/setup', { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
    onError: e => host.notify({ kind: 'error', message: `Couldn't save: ${e.message || e}` })
  })
  const schedule = useMutation({
    mutationFn: () => cronRequest({ action: 'add', name: JOB_NAME, schedule: time, prompt: JOB_PROMPT, deliver: 'local' }),
    onSuccess: res => {
      if (res && res.error) throw new Error(res.error)
      save.mutate({ schedule: `nightly ${time}` })
      qc.invalidateQueries({ queryKey: [ID, 'job'] })
    },
    onError: e => host.notify({ kind: 'error', message: `Couldn't schedule the nightly run: ${e.message || e}` })
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
  const modelDone = !model.follows_main || keepMain
  const nightly = job.data
  const scheduleDone = Boolean(nightly) || setup.schedule === 'manual'
  const hasIdeas = data.cards.length > 0
  const tokens = data.last_run ? Math.round(((data.last_run.input_tokens || 0) + (data.last_run.output_tokens || 0)) / 1000) : null

  return jsx('div', { style: { flex: 1, minHeight: 0, overflow: 'auto' }, children: col({ gap: 0, maxWidth: 720, paddingBottom: 40 }, [
    txt(14, C.s,
      'Idea Board reads your recent chats and what this profile can do, then suggests things Hermes could take off your plate. ' +
      'Nothing runs until you set it up here, and nothing is ever sent for you: an idea goes into a new chat and you press send.',
      { maxWidth: '68ch', paddingBottom: 6 }),

    jsx(Step, {
      n: 1, done: reviewed || Boolean(setup.done), title: 'What it reads',
      children: [
        txt(13, C.t, 'Your own messages from recent chats (not scheduled jobs, subagents or group chats), plus the tools, skills, connected apps and scheduled jobs this profile has. Ideas, dismissals and rules stay in this profile’s plugin data.', { maxWidth: '68ch' }),
        jsx(Field, { label: 'Chats to read', children: jsx(SegmentedControl, {
          value: String(setup.history_days),
          options: [{ id: '7', label: 'Last 7 days' }, { id: '14', label: 'Last 14 days' }, { id: '30', label: 'Last 30 days' }],
          onChange: v => { setReviewed(true); save.mutate({ history_days: Number(v) }) }
        }) }),
        jsx(Field, { label: 'New ideas per run', children: jsx(SegmentedControl, {
          value: String(setup.max_cards),
          options: [{ id: '3', label: '3' }, { id: '6', label: '6' }, { id: '10', label: '10' }],
          onChange: v => { setReviewed(true); save.mutate({ max_cards: Number(v) }) }
        }) })
      ]
    }),

    jsx(Step, {
      n: 2, done: modelDone, title: 'Which model writes the ideas',
      children: [
        txt(13, C.t,
          model.follows_main
            ? `Right now: ${model.name || 'your main model'}, your main model. Each run makes two model calls${tokens ? `; your last run used about ${tokens}k tokens` : ''}. A smaller model is usually enough.`
            : `Right now: ${model.name}, chosen for Idea Board. Each run makes two model calls${tokens ? `; your last run used about ${tokens}k tokens` : ''}.`,
          { maxWidth: '68ch' }),
        row({ gap: 8, flexWrap: 'wrap' }, [
          jsx(Button, {
            variant: 'secondary', size: 'sm',
            onClick: () => host.navigate('/settings?tab=config:model&aux=idea_board'),
            children: model.follows_main ? 'Choose a model for Idea Board' : 'Change model'
          }, 'c'),
          model.follows_main && !keepMain &&
            jsx(Button, { variant: 'text', size: 'sm', onClick: () => setKeepMain(true), children: 'Keep my main model' }, 'k')
        ])
      ]
    }),

    jsx(Step, {
      n: 3, done: scheduleDone, title: 'When it runs',
      children: nightly
        ? [
            txt(13, C.t, `Scheduled every night at ${timeLabel(nightly.schedule) || nightly.schedule}${nightly.state && nightly.state !== 'scheduled' ? ` (${nightly.state})` : ''}. It runs quietly and posts nothing; new ideas appear here.`, { maxWidth: '68ch' }),
            jsx(Button, { variant: 'textStrong', size: 'inline', onClick: () => api.runAction('nav.cron'), children: 'Pause or remove it on Scheduled jobs' })
          ]
        : [
            jsx(SegmentedControl, {
              value: mode, sizing: 'content',
              options: [{ id: 'nightly', label: 'Every night' }, { id: 'manual', label: 'Only when I ask' }],
              onChange: v => {
                setMode(v)
                if (v === 'manual') save.mutate({ schedule: 'manual' })
              }
            }),
            mode === 'nightly'
              ? col({ gap: 10 }, [
                  jsx(Field, { label: 'Time', children: jsx(SegmentedControl, { value: time, options: TIMES, onChange: setTime }) }, 't'),
                  txt(13, C.t, 'Creates a scheduled job in this profile. It reads, thinks and saves ideas here; it never messages you or acts on anything.', { maxWidth: '68ch' }),
                  row({ gap: 8 }, [
                    jsx(Button, { size: 'sm', disabled: schedule.isPending, onClick: () => schedule.mutate(), children: schedule.isPending ? 'Scheduling…' : `Schedule it for ${timeLabel(time)}` }, 's')
                  ])
                ].map((c, i) => jsx('div', { children: c }, i)))
              : txt(13, C.t, 'Make ideas whenever you like from this page, or by sending /idea-board generate in any chat.', { maxWidth: '68ch' })
          ]
    }),

    jsx(Step, {
      n: 4, done: hasIdeas || firstAsked, title: 'Your first ideas',
      children: hasIdeas
        ? [txt(13, C.t, `You already have ${data.cards.length} idea${data.cards.length === 1 ? '' : 's'} waiting.`)]
        : [
            txt(13, C.t, 'Opens a new chat with /idea-board generate ready. Press send; ideas land on this page in a minute or two.', { maxWidth: '68ch' }),
            jsx(Button, { variant: 'secondary', size: 'sm', onClick: () => { setFirstAsked(true); generateNow() }, children: 'Make my first ideas' })
          ]
    }),

    row({ gap: 12, paddingTop: 18, borderTop: `1px solid ${C.line}` }, [
      jsx(Button, { onClick: () => save.mutate({ done: true }, { onSuccess: onDone }), children: hasIdeas ? 'Show my ideas' : 'Finish setup' }, 'd'),
      txt(12, C.t, 'You can change any of this later from Setup.', null)
    ].map((c, i) => (c && c.key ? c : jsx('div', { children: c }, i))))
  ].map((c, i) => jsx('div', { children: c }, i))) })
}

// ---- page --------------------------------------------------------------------------------------
function ListRow({ card, selected, onSelect }) {
  return jsx('button', {
    type: 'button',
    onClick: onSelect,
    'aria-current': selected ? 'true' : undefined,
    style: {
      all: 'unset',
      cursor: 'pointer',
      padding: '8px 10px',
      borderRadius: 6,
      background: selected ? C.soft : 'transparent',
      display: 'flex',
      flexDirection: 'column',
      gap: 2
    },
    children: [
      txt(13.5, C.p, card.title, { fontWeight: selected ? 600 : 500 }),
      txt(12, C.t, card.value_note, null)
    ].map((c, i) => jsx('div', { children: c }, i))
  })
}

function Detail({ card, reasons, onStart, onSnooze, onDismiss, onNote }) {
  return col({ gap: 18, maxWidth: 760, paddingBottom: 32 }, [
    col({ gap: 8 }, [
      txt(22, C.p, card.title, { fontWeight: 600, lineHeight: 1.25, textWrap: 'balance' }),
      jsx(MetaLine, { card })
    ].map((c, i) => jsx('div', { children: c }, i))),
    txt(14, C.s, card.why, { maxWidth: '68ch' }),
    jsx(Evidence, { items: card.evidence }),
    jsx(Caps, { uses: card.uses }),
    jsx(PromptPreview, { card }),
    row({ gap: 8, flexWrap: 'wrap' }, [
      jsxs(Button, { onClick: () => onStart(card), children: [jsx(Codicon, { name: 'comment', style: { marginRight: 6 } }), 'Start in a new chat'] }, 's'),
      jsx(Button, { variant: 'secondary', onClick: () => onSnooze(card), children: 'Not now' }, 'n'),
      jsx(DismissMenu, { card, reasons, onDismiss, onNote }, 'd')
    ]),
    row({ gap: 14, fontSize: 11.5, color: C.q, flexWrap: 'wrap' }, [
      jsxs('span', { children: [jsx(Kbd, { children: '↑' }), ' ', jsx(Kbd, { children: '↓' }), ' move'] }, 1),
      jsxs('span', { children: [jsx(Kbd, { children: 'Enter' }), ' start'] }, 2),
      jsxs('span', { children: [jsx(Kbd, { children: 'N' }), ' not now'] }, 3),
      jsxs('span', { children: [jsx(Kbd, { children: 'D' }), ' dismiss'] }, 4)
    ])
  ].map((c, i) => jsx('div', { children: c }, i)))
}

function Started({ cards }) {
  if (!cards.length) return null
  return col({ gap: 2, paddingTop: 6 }, [
    txt(11.5, C.t, 'Started', { padding: '0 0 4px', textTransform: 'uppercase', letterSpacing: '0.04em' }),
    ...cards.slice(0, 5).map(c =>
      jsx('button', {
        type: 'button',
        disabled: !c.session_id,
        onClick: () => c.session_id && host.openSession(c.session_id),
        style: { all: 'unset', cursor: c.session_id ? 'pointer' : 'default', padding: '6px 10px', borderRadius: 6 },
        children: row({ gap: 6, fontSize: 12.5, color: C.t }, [
          jsx(Codicon, { name: c.outcome === 'done' ? 'check' : 'comment' }, 'i'),
          jsx('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: c.title }, 't')
        ])
      }, c.id)
    )
  ])
}

function Empty({ title, description, action }) {
  return col({ flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16, paddingBottom: 80 }, [
    jsx(EmptyState, { title, description, className: 'min-h-0' }, 'e'),
    action && jsx('div', { children: action }, 'a')
  ])
}

function Header({ data, onRules, onSetup }) {
  return row({ justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, paddingBottom: 14, borderBottom: `1px solid ${C.line}` }, [
    col({ gap: 6 }, [
      txt(20, C.p, 'Idea Board', { fontWeight: 600 }),
      data && data.setup && !data.setup.done ? txt(12, C.t, 'Set up · about two minutes', null) : jsx(Receipt, { run: data && data.last_run })
    ].map((c, i) => jsx('div', { children: c }, i))),
    data && data.setup && data.setup.done &&
      row({ gap: 8 }, [
        jsx(Button, { variant: 'text', size: 'sm', onClick: onSetup, children: 'Setup' }, 'setup'),
        jsx(Button, { variant: 'secondary', size: 'sm', onClick: onRules, children: `What I've learned (${data.rules.length})` }, 'rules')
      ])
  ].map((c, i) => jsx('div', { children: c }, i)))
}

async function generateNow() {
  const ok = await placeInNewChat('/idea-board generate')
  if (!ok) host.notify({ kind: 'error', message: 'Open a new chat and send /idea-board generate.' })
}

function BoardPage() {
  const qc = useQueryClient()
  const board = useBoard()
  const [selected, setSelected] = useState(null)
  const [noteFor, setNoteFor] = useState(null)
  const [rulesOpen, setRulesOpen] = useState(false)
  const [undo, setUndo] = useState(null)
  const [showSetup, setShowSetup] = useState(false)
  const rootRef = useRef(null)
  const data = board.data
  const cards = data ? data.cards : []
  const ordered = useMemo(() => KINDS.flatMap(k => cards.filter(c => c.kind === k.kind)), [cards])
  const current = ordered.find(c => c.id === selected) || ordered[0]

  useEffect(() => {
    rootRef.current && rootRef.current.focus({ preventScroll: true })
  }, [])
  useEffect(() => {
    if (!undo) return
    const t = setTimeout(() => setUndo(null), 10000)
    return () => clearTimeout(t)
  }, [undo])

  const refresh = () => qc.invalidateQueries({ queryKey: BOARD_KEY })
  const nextAfter = card => {
    const i = ordered.findIndex(c => c.id === card.id)
    const next = ordered[i + 1] || ordered[i - 1]
    setSelected(next ? next.id : null)
  }
  const dismiss = useMutation({
    mutationFn: ({ card, reason, note }) => rest(`/cards/${card.id}/dismiss`, { method: 'POST', body: { reason, note } }),
    onMutate: ({ card }) => nextAfter(card),
    onSuccess: (res, { card }) => {
      setUndo({ card, message: res.rule ? `Dismissed. New rule: ${res.rule}` : res.action === 'evidence_consumed' ? 'Dismissed as already handled.' : 'Dismissed.' })
      refresh()
    },
    onError: e => host.notify({ kind: 'error', message: `Couldn't dismiss: ${e.message || e}` })
  })
  const snooze = useMutation({
    mutationFn: card => rest(`/cards/${card.id}/snooze`, { method: 'POST', body: { days: 7 } }),
    onMutate: card => nextAfter(card),
    onSuccess: (_r, card) => {
      setUndo({ card, message: 'Hidden for a week.' })
      refresh()
    },
    onError: e => host.notify({ kind: 'error', message: `Couldn't snooze: ${e.message || e}` })
  })
  const undoMut = useMutation({
    mutationFn: card => rest(`/cards/${card.id}/undo`, { method: 'POST' }),
    onSuccess: (_r, card) => {
      setUndo(null)
      setSelected(card.id)
      refresh()
    }
  })
  const start = card => {
    startIdea(card).finally(refresh)
  }
  const onDismiss = (card, reason, note) => dismiss.mutate({ card, reason, note })

  const onKeyDown = e => {
    if (!current || e.target !== rootRef.current) return
    const i = ordered.findIndex(c => c.id === current.id)
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      const n = ordered[Math.max(0, Math.min(ordered.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))]
      n && setSelected(n.id)
    } else if (e.key === 'Enter' || e.key === 's') {
      e.preventDefault()
      start(current)
    } else if (e.key === 'n') {
      snooze.mutate(current)
    } else if (e.key === 'd') {
      setNoteFor(current)
    }
  }

  let body
  if (board.isLoading) {
    body = row({ flex: 1, justifyContent: 'center' }, jsx(Loader, {}))
  } else if (board.isError) {
    body = jsx(Empty, {
      title: "Idea Board's backend isn't on for this profile",
      description:
        'Turn on Idea Board in Settings → Plugins, and enable its agent half: hermes plugins enable idea-board. Then restart the gateway.',
      action: jsx(Button, { variant: 'secondary', onClick: () => host.navigate('/settings/plugins'), children: 'Open Plugins' })
    })
  } else if (data.setup && (!data.setup.done || showSetup)) {
    body = jsx(SetupView, { data, onDone: () => setShowSetup(false) })
  } else if (!cards.length) {
    body = jsx(Empty, {
      title: data.last_run ? 'No new ideas right now' : 'No ideas yet',
      description: data.last_run
        ? 'The last run found nothing worth your time that you haven’t already seen. The next nightly run looks again.'
        : 'Idea Board reads your recent chats and what this profile can do, then suggests things Hermes could take off your plate. It runs nightly once you schedule it.',
      action: jsx(Button, { onClick: generateNow, children: 'Generate ideas now' })
    })
  } else {
    body = jsxs('div', {
      style: { display: 'grid', gridTemplateColumns: '320px minmax(0, 1fr)', gap: 36, flex: 1, minHeight: 0 },
      children: [
        col({ gap: 18, overflow: 'auto', borderRight: `1px solid ${C.line}`, paddingRight: 18, paddingBottom: 24 }, [
          ...KINDS.map(k => {
            const items = ordered.filter(c => c.kind === k.kind)
            if (!items.length) return null
            return col({ gap: 2 }, [
              row({ gap: 6, fontSize: 11.5, color: C.t, textTransform: 'uppercase', letterSpacing: '0.04em', padding: '0 0 4px' }, [
                jsx(Codicon, { name: k.icon }, 'i'),
                jsx('span', { children: `${k.label} · ${items.length}` }, 't')
              ]),
              ...items.map(c => jsx(ListRow, { card: c, selected: current && c.id === current.id, onSelect: () => setSelected(c.id) }, c.id))
            ].map((c, i) => (c && c.key ? c : jsx('div', { children: c }, `h${i}`))))
          }).filter(Boolean).map((c, i) => jsx('div', { children: c }, `g${i}`)),
          jsx(Started, { cards: data.started }, 'started')
        ]),
        col({ gap: 14, overflow: 'auto', minHeight: 0 }, [
          undo &&
            row({ gap: 12, fontSize: 12.5, color: C.s, padding: '8px 12px', borderRadius: 6, background: C.soft }, [
              jsx('span', { style: { flex: 1 }, children: undo.message }, 'm'),
              jsx(Button, { variant: 'textStrong', size: 'inline', onClick: () => undoMut.mutate(undo.card), children: 'Undo' }, 'u')
            ]),
          current && jsx(Detail, { card: current, reasons: data.reasons, onStart: start, onSnooze: c => snooze.mutate(c), onDismiss, onNote: setNoteFor })
        ].filter(Boolean).map((c, i) => jsx('div', { children: c }, i)))
      ]
    })
  }

  return jsxs('div', {
    ref: rootRef,
    tabIndex: 0,
    onKeyDown,
    style: { height: '100%', display: 'flex', flexDirection: 'column', padding: '24px 36px 0', gap: 16, minHeight: 0, outline: 'none' },
    children: [
      jsx(Header, { data, onRules: () => setRulesOpen(true), onSetup: () => setShowSetup(true) }),
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
