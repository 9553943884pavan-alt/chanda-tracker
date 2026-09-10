import { useEffect, useState } from 'react'
import api from '../api'

export default function Announcements() {
  const [broadcasts, setBroadcasts] = useState(null)

  useEffect(() => {
    async function loadBroadcasts() {
      try {
        const { data } = await api.get('/broadcasts')
        setBroadcasts(data)
      } catch {
        setBroadcasts([])
      }
    }
    loadBroadcasts()
  }, [])

  if (broadcasts === null || broadcasts.length === 0) return null

  return (
    <section className="mx-auto max-w-6xl rounded-2xl border border-teal-200 bg-teal-50/60 p-5 shadow-[0_18px_50px_rgba(56,73,64,0.08)] sm:p-7">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-700">Announcements</p>
      <h2 className="mt-2 font-display text-2xl font-semibold text-stone-950">Messages from your event lead</h2>
      <div className="mt-5 space-y-3">
        {broadcasts.map((broadcast) => (
          <div key={broadcast.id} className="rounded-xl border border-teal-200 bg-[#fffdf8]/90 px-4 py-3">
            <p className="text-sm leading-6 text-stone-800">{broadcast.message}</p>
            <p className="mt-2 text-xs text-stone-500">
              — {broadcast.sent_by}
              {broadcast.sent_at ? ` · ${new Date(broadcast.sent_at).toLocaleString()}` : ''}
              {(broadcast.filter_role !== 'all' || broadcast.filter_year || broadcast.filter_branch || broadcast.filter_gender) && (
                <> · <span className="uppercase font-bold text-teal-700">
                  {[
                    broadcast.filter_role === 'collector' ? 'Collectors only' : broadcast.filter_role === 'giver' ? 'Givers only' : 'Everyone',
                    broadcast.filter_year ? `Year ${broadcast.filter_year}` : 'All years',
                    broadcast.filter_branch || 'All branches',
                    broadcast.filter_gender || 'All genders',
                  ].join(' · ')}
                </span></>
              )}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
