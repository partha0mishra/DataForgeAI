view: user_sessions {
  sql_table_name: `your-gcp-project.analytics_reporting.user_sessions` ;;

  dimension: user_pseudo_id {
    type: string
    sql: ${TABLE}.user_pseudo_id ;;
    primary_key: yes
  }

  dimension: session_date {
    type: date
    datatype: date
    sql: ${TABLE}.session_date ;;
  }

  dimension: session_id {
    type: number
    sql: ${TABLE}.session_id ;;
  }

  dimension_group: session_start {
    type: time
    timeframes: [time, date, week, month, quarter, year]
    sql: ${TABLE}.session_start ;;
  }

  dimension: session_duration_seconds {
    type: number
    sql: ${TABLE}.session_duration_seconds ;;
  }

  dimension: session_duration_minutes {
    type: number
    sql: ${session_duration_seconds} / 60.0 ;;
    value_format_name: decimal_2
  }

  dimension: device_category {
    type: string
    sql: ${TABLE}.device_category ;;
  }

  dimension: country {
    type: string
    map_layer_name: countries
    sql: ${TABLE}.country ;;
  }

  dimension: traffic_source {
    type: string
    sql: ${TABLE}.traffic_source ;;
  }

  dimension: landing_page {
    type: string
    sql: ${TABLE}.landing_page ;;
  }

  dimension: converted {
    type: yesno
    sql: ${TABLE}.purchases > 0 ;;
  }

  measure: count_sessions {
    type: count
    drill_fields: [user_pseudo_id, session_start_time, device_category, country]
  }

  measure: total_page_views {
    type: sum
    sql: ${TABLE}.page_views ;;
  }

  measure: avg_page_views_per_session {
    type: average
    sql: ${TABLE}.page_views ;;
    value_format_name: decimal_2
  }

  measure: total_conversions {
    type: sum
    sql: ${TABLE}.purchases ;;
  }

  measure: conversion_rate {
    type: number
    sql: SAFE_DIVIDE(${total_conversions}, ${count_sessions}) ;;
    value_format_name: percent_2
  }

  measure: avg_session_duration {
    type: average
    sql: ${session_duration_seconds} ;;
    value_format_name: decimal_2
  }
}
