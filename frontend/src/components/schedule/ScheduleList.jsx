import { useMemo, useState } from 'react'
import ScheduleItemCard from './ScheduleItemCard'

// 일정 목록 전체 담당
function ScheduleList({ schedules, selectedDate, isTodaySelected = false, onToggle }) {
  const [expandedTimeKeys, setExpandedTimeKeys] = useState(() => new Set())
  const todayScheduleGroups = useMemo(
    () => groupSchedulesByTime(schedules),
    [schedules],
  )

  if (!schedules.length) {
    return (
      <section className="schedule-list schedule-list--empty">
        <p className="schedule-list__empty-title">등록된 복약 일정이 없습니다.</p>
        <p className="schedule-list__empty-subtitle">
          다른 날짜를 선택하거나 새 복약 일정을 추가해보세요.
        </p>
      </section>
    )
  }

  const handleToggleGroup = (timeKey) => {
    setExpandedTimeKeys((prev) => {
      const next = new Set(prev)

      if (next.has(timeKey)) {
        next.delete(timeKey)
      } else {
        next.add(timeKey)
      }

      return next
    })
  }

  if (isTodaySelected) {
    return (
      <section className="schedule-list">
        {todayScheduleGroups.map((group) => {
          if (group.items.length === 1) {
            const item = group.items[0]

            return (
              <ScheduleItemCard
                key={item.id}
                item={{ ...item, time_to_take: group.timeKey }}
                onToggle={() => onToggle(selectedDate, item)}
              />
            )
          }

          const isExpanded = expandedTimeKeys.has(group.timeKey)

          return (
            <div className="schedule-list__time-group" key={group.timeKey}>
              <button
                type="button"
                className="schedule-list__time-group-button"
                onClick={() => handleToggleGroup(group.timeKey)}
                aria-expanded={isExpanded}
              >
                <span className="schedule-list__time-group-time">
                  {group.timeKey}
                </span>
                <span className="schedule-list__time-group-title">
                  복약일정 +{group.items.length}
                </span>
              </button>

              {isExpanded ? (
                <div className="schedule-list__time-group-items">
                  {group.items.map((item) => (
                    <ScheduleItemCard
                      key={item.id}
                      item={{ ...item, time_to_take: group.timeKey }}
                      onToggle={() => onToggle(selectedDate, item)}
                    />
                  ))}
                </div>
              ) : null}
            </div>
          )
        })}
      </section>
    )
  }

  return (
    <section className="schedule-list">
      {schedules.map((item) => (
        <ScheduleItemCard
          key={item.id}
          item={item}
          onToggle={() => onToggle(selectedDate, item)}
        />
      ))}
    </section>
  )
}

function groupSchedulesByTime(schedules = []) {
  const groupMap = new Map()

  schedules.forEach((item) => {
    const timeKey = normalizeScheduleTime(item.time_to_take)

    if (!groupMap.has(timeKey)) {
      groupMap.set(timeKey, [])
    }

    groupMap.get(timeKey).push(item)
  })

  return Array.from(groupMap.entries())
    .map(([timeKey, items]) => ({ timeKey, items }))
    .sort((a, b) => a.timeKey.localeCompare(b.timeKey))
}

function normalizeScheduleTime(value) {
  if (!value) {
    return '--:--'
  }

  const text = String(value).trim()
  const timeMatch = text.match(/(?:T|\s)?(\d{1,2}):(\d{2})(?::\d{2})?/)

  if (!timeMatch) {
    return '--:--'
  }

  return `${timeMatch[1].padStart(2, '0')}:${timeMatch[2]}`
}

export default ScheduleList
