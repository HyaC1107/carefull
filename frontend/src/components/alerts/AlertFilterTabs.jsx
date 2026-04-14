function AlertFilterTabs({ activeFilter, tabs, onChangeFilter }) {
  return (
    <section className="alert-filter-tabs">
      {tabs.map((tab) => {
        const isActive = tab.key === activeFilter

        return (
          <button
            key={tab.key}
            type="button"
            className={`alert-filter-tabs__button ${
              isActive ? 'alert-filter-tabs__button--active' : ''
            }`}
            onClick={() => onChangeFilter(tab.key)}
          >
            {tab.label} ({tab.count})
          </button>
        )
      })}
    </section>
  )
}

export default AlertFilterTabs