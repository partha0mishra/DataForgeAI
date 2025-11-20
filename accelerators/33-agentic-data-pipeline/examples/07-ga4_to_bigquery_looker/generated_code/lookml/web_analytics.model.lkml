connection: "bigquery_analytics"

include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lookml"

datagroup: ga4_analytics_default_datagroup {
  sql_trigger: SELECT MAX(session_date) FROM analytics_reporting.user_sessions ;;
  max_cache_age: "4 hours"
}

persist_with: ga4_analytics_default_datagroup

explore: user_sessions {
  label: "User Sessions"
  description: "GA4 user session data with engagement metrics"

  join: page_views {
    type: left_outer
    sql_on: ${user_sessions.session_date} = ${page_views.page_view_date} ;;
    relationship: one_to_many
  }

  join: conversion_funnel {
    type: left_outer
    sql_on: ${user_sessions.session_date} = ${conversion_funnel.event_date} ;;
    relationship: many_to_one
  }

  join: traffic_sources {
    type: left_outer
    sql_on: ${user_sessions.session_date} = ${traffic_sources.traffic_date}
        AND ${user_sessions.traffic_source} = ${traffic_sources.source} ;;
    relationship: many_to_one
  }
}

explore: page_views {
  label: "Page Performance"
  description: "Page-level engagement metrics"
}

explore: conversion_funnel {
  label: "Conversion Funnel"
  description: "User journey conversion rates"
}

explore: traffic_sources {
  label: "Traffic Sources"
  description: "Marketing channel performance"
}
