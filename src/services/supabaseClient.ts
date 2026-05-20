import { createClient, type AuthChangeEvent, type Session } from '@supabase/supabase-js'

export type WorkbenchState = {
  courses: unknown[]
  notes: Record<string, string>
  videos: Record<string, string>
  shortcuts: unknown
  studySplitRatio: number | null
  studySideNotesWidth: number | null
  studyNotePosition: string | null
}

export type RemoteWorkbenchState = {
  state: WorkbenchState | null
  updatedAt: string | null
}

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined
const supabasePublishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined

export const supabaseConfigError = !supabaseUrl || !supabasePublishableKey
  ? '请先配置 VITE_SUPABASE_URL 和 VITE_SUPABASE_PUBLISHABLE_KEY 后再使用账号同步。'
  : ''

export const supabase = supabaseConfigError
  ? null
  : createClient(supabaseUrl!, supabasePublishableKey!, {
      auth: {
        persistSession: true,
        autoRefreshToken: true
      }
    })

function requireSupabase() {
  if (!supabase) {
    throw new Error(supabaseConfigError)
  }

  return supabase
}

export async function getCurrentSession() {
  const client = requireSupabase()
  const { data, error } = await client.auth.getSession()

  if (error) throw error
  return data.session
}

export function onAuthStateChange(callback: (event: AuthChangeEvent, session: Session | null) => void) {
  const client = requireSupabase()
  const { data } = client.auth.onAuthStateChange(callback)

  return () => data.subscription.unsubscribe()
}

export async function signUpWithEmail(email: string, password: string) {
  const client = requireSupabase()
  const { data, error } = await client.auth.signUp({ email, password })

  if (error) throw error
  return data
}

export async function signInWithEmail(email: string, password: string) {
  const client = requireSupabase()
  const { data, error } = await client.auth.signInWithPassword({ email, password })

  if (error) throw error
  return data
}

export async function signOut() {
  const client = requireSupabase()
  const { error } = await client.auth.signOut()

  if (error) throw error
}

export async function loadRemoteWorkbenchState(userId: string): Promise<RemoteWorkbenchState> {
  const client = requireSupabase()
  const { data, error } = await client
    .from('workbench_states')
    .select('state, updated_at')
    .eq('user_id', userId)
    .maybeSingle()

  if (error) throw error
  const state = (data?.state ?? null) as WorkbenchState | null

  return {
    state,
    updatedAt: data?.updated_at ?? null
  }
}

export async function saveRemoteWorkbenchState(userId: string, state: WorkbenchState) {
  const client = requireSupabase()
  const { error } = await client
    .from('workbench_states')
    .upsert({
      user_id: userId,
      state,
      updated_at: new Date().toISOString()
    })

  if (error) throw error
}
