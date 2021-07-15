library(shiny)
library(bslib)
library(httr)
library(jsonlite)
library(plotly)
library(shiny.i18n)
library(shinyWidgets)
library(tidyverse)

source("scripts/appendix.R")
root_path <<- "../../"
config <- read_ini(paste0(root_path, "conf/conf.ini"))
quant_log <- paste0(root_path, "visualization/logs/quant_log.csv")
sqa_log <- paste0(root_path, "visualization/logs/sqa_log.csv")
i18n <- Translator$new(translation_csvs_path = paste0(root_path, "visualization/checker/lang/"))
i18n$set_translation_language("en")
PROD <- config$MODE$PRODUCTION %>% toupper %>% parse(text=.) %>% eval
# if (!PROD){Sys.setenv(
#   "API_HOST" = "localhost",
#   "API_PORT" = 5000
# )}

limit <- 20
api_server <- Sys.getenv(c("API_HOST"))
api_port <- Sys.getenv(c("API_PORT"))

hue <- list(
  dark_blue = '#242654',
  blue = '#5c7fd3',
  green = '#5cf1bb',
  grey = '#bcccdbff',
  grey_bg = "#EEF3F6",
  white = '#ffffff',
  sucess = '#b8e994',
  info = '#60a3bc',
  warning = '#f6b93b',
  danger = '#e55039',
  light = '#E9E9EE'
)

theme <- bs_theme(
  version = 4,
  bootswatch = 'litera',
  bg = hue$white,
  fg = hue$dark_blue,
  primary = hue$blue,
  secondary = hue$green,
  success = hue$sucess,
  info = hue$info,
  warning = hue$warning,
  danger = hue$danger,
  heading_font = font_google('Playfair Display'),
  base_font = font_google('Lato'),
  "font-size-base" = "0.9rem",
  "font-weight-base" = "500",
  "line-height-base" = 1.2
)

options(
  spinner.color = hue$blue,
  spinner.size = 1,
  spinner.type = 7,
  warn = -1
)


##########################################################################
######################     API      ######################################
##########################################################################


get_indicator <- function(indicator, ...){
  #' Get API indicator response
  #' indicator: str. One of corpus, quantities or scienceqa
  #' ...: indicator kwargs
  #' :return: list
  
  response <- NULL
  main <- paste0('http://', api_server, ':', api_port, '/', indicator)
  query <- list(...)
  request <- GET(main, query = query)
  if(request$status_code == 200){
    response <- request %>% 
      content(as = "text", encoding = "UTF-8") %>% 
      fromJSON %>% as_tibble()
  }
  return(response)
}


create_task <- function(
  first, second, relation,
  index = "prod_epmc_articles",
  pulling = "eqa"){
  #' Create task
  #' first, second: str.
  #' relation: str.
  #' index: str.
  #' pulling: str or NULL
  #' :return: task_id. str.
  
  task_id <- NULL
  main <- paste0('http://', api_server, ':', api_port, '/indicators/')
  query <- list(
    first = first,
    second = second,
    relation = relation,
    index = index,
    pulling = pulling
  )
  request <- POST(main, query = query)
  
  if(request$status_code == 200){
    task_id <- request %>% content %>% .$id
  }
  
  return(task_id)
}


get_task <- function(task_id, time = 8){
  #' Pull task if done
  #' taskid: str
  #' time: int, in second, to sleep between requests
  #' :return: list of corpus and articles or NULL
  
  query <- paste0('http://', api_server, ':', api_port, '/indicators/', task_id)
  request <- GET(query)
  status <- request$status_code
  
  while(status == 202){
    Sys.sleep(time)
    request <- GET(query)
    status <- request$status_code
  }
  if(status == 200){
    response <- request %>% 
      content(as = "text", encoding = "UTF-8") %>% 
      fromJSON
  }else{
    response <- NULL
  }
  
  return(response)
}

##########################################################################
######################    UTILS     ######################################
##########################################################################


get_url <- function(url, doi){
  if (is.valid(url)){
    url <- url
  } else if (is.valid(doi)) {
    url <- paste0('https://dx.doi.org/', doi)
  } else {
    url <- NA
  }
  
  url
}

to_url <- function(title, url, doi, class){
  #' Format title to html a
  #' title: str
  #' utl: str or NA
  #' class: str
  #' :return: str, formated html
  
  url <- get_url(url, doi)
  
  if (is.valid(url)){
    url <- paste0(
      '<a class="', class,
      '" target="_blank" href="',
      url, '">', title, '</a>')
  } else {
    url <- paste0(
      '<span class="', class,
      '">', title, '</span>')
  }
  url
}


highlight_quant <- function(label, least, most){
  quantities <- c()
  for (quant in c(least, most)){
    hg <- paste0(
      '(', as.character(quant), '0?|',
      as.character(as.double(quant)*100),
      '0?\\s?%)'
    )
    quantities <- c(quantities, hg)
  }
  paste0(
    '(', label, ')(.*?)',
    quantities[1], '(.*?)',
    quantities[2]
  )
}


clean_authors <- function(x, thres = 3){
  #' Format authors
  #' x: list of authors
  #' thres: int, threshold of diplayed authors
  #' :return: string
  
  authors <- x %>% unlist
  if (length(authors)>thres){
    authors <- authors[1:thres] %>% paste(collapse = ", ") %>% paste("...")
  } else {
    authors <- authors %>% paste(collapse = ", ")
  }
  authors
}


collapside <- function(text, y, max_length = 80){
  #' Wrap text for UI collapsing
  #' text: str
  #' y: int, for id #more_y
  #' max_length: int, to show
  #' :return: formated HTML string
  
  pattern <- paste0("([^<>]{1,", max_length, "})?(?![^<>]*>)")
  showed <- text %>% str_squish %>%
    str_extract_all(pattern) %>% 
    unlist %>% 
    Filter(f = function(x){nchar(x)>1}, .) %>% .[1]
  parts <- text %>% strsplit(showed, fixed = TRUE) %>% unlist

  if (str_count(parts[1], "<span class='hg'>") > str_count(parts[1], "</span>")){
    sep <- paste0("</span><span class='collapse' id='more_", y, "'><span class='hg'>")
  } else {
    sep <- paste0("<span class='collapse' id='more_", y, "'>")
  }
  
  str_c(
    parts[1], showed, sep, parts[2],
    "</span><span><a href='#more_", y,
    "'data-toggle='collapse'>... ",
    "<i class='fa fa-caret-down'></i></a></span>"
  )
}


htmltext <- function(htmlString) {
  #' Return text from html string
  #' :return: string

  return(gsub("<.*?>", "", htmlString))
}


ing <- function(verb) {
  #' verb to ing
  #' :return: string

  if (nchar(verb) < 4){
    verb <- paste0(verb, substring(verb, nchar(verb)))
  }
  if (substring(verb, nchar(verb)) == 'e'){
    verb <- paste0(substr(verb, 0, nchar(verb)-1), 'ing')
  } else {
    verb <- paste0(verb, 'ing')
  }
  return(verb)
}

i_ <- function(...) i18n$t(...)


bicss <- function(x, base, high){
  #' Two color, base and high
  #' x: values vector
  #' base: color base
  #' high: color high
  #' :return: color vector x size

  color <- rep(base, length(x))
  color[which.max(x)] <- high
  color
}


balanced <- function(sqa_summary, z = 1.96){
  #' Proportion comparaison z-test
  #' sqa_summary: tibble
  #' z: threshold
  #' :return: balanced (bool), z value

  decisions <- sqa_summary %>% 
    filter(answer%in%c('yes','no'))
  
  balanced <- FALSE
  z_ <- NULL
  
  if(is.valid(is.valid(decisions) & nrow(decisions) > 1)){
    a <- decisions %>% filter(answer == 'yes')
    #pa <- a$confidence/100
    #na <- a$response
    pa <- a$response/100
    na <- decisions$response %>% sum
    
    b <- decisions %>% filter(answer == 'no')
    #pb <- a$confidence/100
    #nb <- a$response
    pb <- b$response/100
    nb <- decisions$response %>% sum
    
    pc <- (na*pa + nb*pb)/(na+nb)
    qc <- 1 - pc
    
    z_ <- (pa - pb)/sqrt(qc*pc/na + qc*pc/nb)
    
    
    balanced <- all(
      na*pa >= 5,
      na*(1-pa) >= 5,
      nb*pb >= 5,
      nb*(1-pb) >= 5,
      abs(z_) <= z
    )
    
  }
  
  list(balanced = balanced, z = z_)
}

##########################################################################
######################    CORPUS    ######################################
##########################################################################


plot_corpus <- function(corpus){
  #' Interactive plot of corpus
  #' corpus: list of year: value
  #' :return: plotly
  
  corpus <- corpus %>% 
    mutate(year = as.integer(str_extract(publication_date, "[^-]+"))) %>% 
    filter(year < as.integer(format(Sys.Date(), "%Y"))) %>% 
    group_by(year) %>% 
    summarise(publications = n()) %>% 
    dplyr::ungroup() %>% {
      if(nrow(.) > 0){
        complete(
          .,
          year = min(year):max(year),
          fill = list(publications = 0)
        )
      } else {
        tibble(year = integer(), publications = integer())
      }
    }
  
  if (nrow(corpus)){
    ploted <- corpus %>% ggplot +
      aes(year, publications) +
      geom_area(alpha = .5, fill = hue$dark_blue) + 
      geom_line(color = hue$dark_blue) +
      theme(
        panel.background = element_rect(fill = hue$grey_bg),
        plot.background = element_rect(fill = "transparent", color = NA)
      )
    
    
    chart <- ggplotly(ploted) %>% 
      plotly::config(displayModeBar = F) %>% 
      layout(
        xaxis = list(fixedrange = T),
        yaxis = list(fixedrange = T))
  } else {
    
    chart <- plotly_empty(type = "scatter", mode = "markers") %>%
      plotly::config(displayModeBar = F) %>%
      layout(
        title = list(
          text = paste("No publication before", format(Sys.Date(), "%Y")),
          yref = "paper",
          y = 0.5,
          plot_bgcolor  = 'transparent',
          paper_bgcolor = 'transparent',
          xaxis = list(fixedrange = T),
          yaxis = list(fixedrange = T)
        )
      )
  }
  
  chart
  
}


##########################################################################
####################    QUANTITIES    ####################################
##########################################################################


significant <- function(min_value, max_value, rule){
  #' Returns the rule if it is within the range, for IC
  #' otherwise it returns the closest value.
  #' **_value, rule: (double, int)
  #' :return: (double, int)
  
  values <- sort(c(min_value, max_value))
  testing <- sum(values < rule)
  if (between(rule, values[1], values[2])) {
    quantity <- rule
  } else if (testing == 2) {
    quantity <- max_value
  } else if (testing == 0) {
    quantity <- min_value
  } else {
    quantity <- na.omit(c(min_value, max_value))
  }
  
  return(quantity)
}



plot_quantities <- function(quant, rule = 1){
  #' Interactive plot of quantities
  #' quant: dataframe of title, text,
  #'   quantityLeast and quantityMost
  #' :return: plotly
  
  ic_data <- quant %>% 
    mutate(
      y = as.character(1:n()),
      text = str_wrap(text) %>% paste('\n'),
      text = str_replace(
        text,
        paste0(
          '(', label, ')(.*?)(',
          as.character(quantityLeast), ')(.*?)(',
          as.character(quantityMost), ')'
        ),
        paste0('<b>\\1</b>\\2<b>\\3</b>\\4<b>\\5</b>')
      ),
      quantity = map2_dbl(quantityLeast, quantityMost, significant, rule=rule),
      over = case_when(
        quantity < rule ~ "0",
        quantity == rule ~ "1",
        TRUE ~ "2"
      )
    ) %>% 
    select(y, text, quantity, over)
  
  
  ploted <- ggplot()  + 
    geom_point(
      data = ic_data,
      aes(quantity, y, color = over, text = text),
      shape = 19, size = 3
    ) + geom_vline(xintercept = rule, alpha = 0.2) +
    scale_y_discrete(limits = rev) +
    scale_color_manual(
      values = c(
        "0" = hue$sucess,
        "1" = hue$warning,
        "2" = hue$danger)
    ) + theme(
      axis.ticks = element_blank(),
      axis.text.y = element_blank(),
      axis.title.y = element_blank(),
      legend.position = "none",
      panel.background = element_rect(fill = hue$light),
      plot.background = element_rect(fill = "transparent", color = NA)
    )
  
  sizes <- c(
    '1' = 210,
    '2' = 225,
    '3' = 290,
    '4' = 420
  )
  x <- quant %>% pull(text) %>% nchar %>% sum
  height <- if (nrow(quant)>4) {208.5*log(x) -1000} else {sizes[[as.character(nrow(quant))]]}
  
  ggplotly(
    p = ploted,
    tooltip = c("text"),
    height = height
  ) %>% layout(
    # xaxis = list(range = c(0,3)),
    yaxis = list(fixedrange = TRUE),
    dragmode = 'pan'
  ) %>% plotly::config(
    displaylogo = FALSE,
    modeBarButtonsToRemove = c(
      "zoomIn2d", "zoomOut2d", "lasso2d",
      "zoom2d", "select2d", "hoverClosestCartesian",
      "hoverCompareCartesian", "autoScale2d", "resetScale2d"
    )
  )
}


##########################################################################
####################      ANSWERS     ####################################
##########################################################################

format_sqa <- function(row, quantities){
  #' Convert sqa output to html
  #' row: dataframe where columns index must be
  #'  1: y, row index
  #'  2: title
  #'  3: authors
  #'  4: response
  #'  5: date
  #'  6: id
  #'  7: URL
  #' quantities: dataframe of quantities
  #' :return: shiny fluidRow

  y <- row[1]
  class <- ifelse(as.integer(row[1])%%2==0, "even-table", "odd-table")
  title <- h5(class = 'text-primary pb-0 mb-3 mt-2', shiny::HTML(row[2]))
  authors <- paste(row[5], ' | ', row[3]) %>% 
    h6(class = 'pt-0 mb-0 mt-3')
  text <- row[4] %>% shiny::HTML() %>% 
    p(class = 'font-weight-light my-1')
  abstract <- row[4] %>% htmltext %>% substr(0, 150) %>% paste('...') %>% p(class = 'font-weight-light')
  quantities <- quantities %>% filter(id == row[6])
  
  more <- fluidRow(
    class = "px-2 px-md-4 details justify-content-center justify-content-md-start",
    checkboxGroupButtons(paste0('hg_', y), choices = c(`<i class='fas fa-highlighter'></i>Highlights` = 1), status = 'primary'),
    checkboxGroupButtons(paste0('q_', y), choices = c(`<i class='fas fa-superscript'></i>Relative risk` = 1), status = if(nrow(quantities)){'primary'} else {'primary d-none'}),
    if(is.valid(row[7])) {div(class = 'form-group', a(href = row[7], class = 'btn btn-primary', target = "_blank", span(tags$i(class='fas fa-book-open'), i_("Full Text"))))} else {NULL}
  )
  
  
  div(class = paste(class, "px-3 py-2"),
    fluidRow(
      column(8,
        authors, title,
        conditionalPanel(condition = paste0('input.hg_', y, '!=1'), abstract),
        more
      ),
      column(4,
        class = "align-self-center",
        div(
          class = "card col-12 bg-grey border-grey py-1",
          formattableOutput(paste0("out_", y))
        ))
    ),
    fluidRow(
      column(12,
        conditionalPanel(
          condition = paste0('input.hg_', y, '==1'),
          class = "container py-3",
          h4(class = 'mt-0', "Highlights"),
          text
        ),
        conditionalPanel(
          condition = paste0('input.q_', y, '==1'),
          class = "container py-3",
          h4(class = 'mt-0', "Quantities"),
          fluidRow(
            class = "align-items-center",
            column(6,
              class = "mb-5 mb-md-0",
              div(
                tags$small("The", a("relative risk (RR)", href = 'https://en.wikipedia.org/wiki/Relative_risk', target = '_blank'), "is the ratio of the probability of the disease in a group exposed to the agent to the probability of the disease in an unexposed group."),
                tags$small("If the confidence interval includes 1, then it means that no correlation between agent and disease was found, if it does not, then, the study finds a correlation between agent and disease.")
              ),
              DT::dataTableOutput(paste0("quant_art_", y))
            ),
            column(6,
              class = "mb-5 mb-md-0",
              cardBox(
                withSpinner(
                  plotlyOutput(paste0("quant_plot_", y)),
                  hide.ui = F),
                status = "light",
                header = p(
                  class = "text-right m-0 mt-2",
                  strong(i_("Relevant confidence intervals"))
                ),
                header_class = "border-bottom-0 bg-light",
                body_class = "bg-light pb-4"
              )
            )
          )
        )
      )
    ),
   tags$small(class = 'text-right container-fluid pb-2 d-block',
     actionLink(
       paste0("sqa_rp_", y),
       class = 'px-4',
       label = i_('Report'),
       icon = shiny::icon('flag'),
       onclick = 'get_id(this.id)'))
  )
}


sqa_subplot <- function(row, s=10, t=4){
  #' Convert sqa answer to ggplot bar
  #' row: named vector 1x3
  #' :return: ggplot
  
  row %>% gather(response, value) %>%  
    mutate(text = sprintf("%0.2f", value)) %>% 
    bind_rows(tibble(response = c('neutral', 'no', 'yes'), value=0)) %>% 
    ggplot + aes(response, value, label = text, col = response) + 
    geom_line(lineend = "round", lwd = s, alpha = .8) +
    coord_flip(ylim = c(-5,110)) +
    geom_text(hjust=.6, col=hue$dark_blue, size=t) +
    scale_color_manual(values = c(
      "neutral" = hue$grey,
      "no" = hue$danger,
      "yes" = hue$green)) +
    theme(
      panel.background = element_rect(fill = "transparent", color = NA),
      plot.background = element_rect(fill = "transparent", color = NA),
      panel.grid.major = element_blank(),
      panel.grid.minor = element_blank(),
      axis.ticks = element_blank(),
      axis.text.x = element_blank(),
      axis.title.y = element_blank(),
      axis.title.x = element_blank(),
      legend.position = "none",
    )
}


sqa_subtable <- function(row){
  row %>% gather(response, value) %>% 
    mutate(response = factor(response, levels = c('yes', 'no', 'neutral'))) %>% 
    dplyr::arrange(response) %>% 
    mutate(
      response = as.character(response),
      response = i_(response),
      response = str_to_title(response),
      value = percent(value/100)
    ) %>% 
    select(response, bar = value, value = value) %>% 
    formattable(list(
      bar = formatter("span", style = x ~ formattable::style(
        display = 'inline-block',
        "background-color" = ifelse(.$response == i_('Yes'), hue$green, ifelse(.$response == i_('No'), hue$danger, hue$grey)),
        color = "transparent",
        "border-radius" = "15px",
        "white-space" = "nowrap",
        width = x
      )),
      value = formatter("span", style = x ~ formattable::style(
        display = "inline-block",
        padding = ".2em .5em .2em .2em",
        background = bicss(c(x), hue$grey, hue$warning),
        "max-height" = "25px",
        "border-radius" = "0 30px 30px 0",
        "font-weight" = "bolder",
        width = "100%"
      ))
    ), align = c('r', 'l', 'c')) %>% 
    renderFormattable()
}


vote <- function(data, voting = 'soft'){
  #' SUmmarise sqa answer output by voting
  #' data: dataframe w/ no, yes, neutral
  #' voting: str. soft or hard
  #' :return: tible 1x3
  
  if(voting=='soft'){
    data <- data %>% 
      colMeans %>% round(2) %>% 
      as.list %>% as_tibble
  }else{
    data <- data %>% 
      rowwise() %>% 
      mutate(response = which.max(c(no, yes, neutral))) %>% 
      as_tibble %>% group_by(response) %>%
      summarise(value = round(n()*100/nrow(.), 2)) %>% 
      mutate(response = recode(response,
                               `1` = "no", `2` = "yes", `3` = "neutral"
      )) %>% spread(response, value)
  }
  
  data
}

table_quant_qa <- function(activeqa, quantities, i){
  #' Render quantities table
  #' activeqa: active table of answer
  #' quantities: table of quantities
  #' :return: renderDataTable
  
  id_ <- activeqa %>% pull(id) %>% .[i]
  quantities <- quantities %>% filter(id == id_)
  
  renderDataTable({
    req(quantities)
    req(nrow(quantities) > 0)
    
    columnDefs <- list(
      #Relevance
      list(targets = 0, visible = F),
      #Articles
      list(targets = 1, searchable = T),
      #Report
      list(targets = 4, orderable = F)
    )
    
    n <- ceiling(nrow(quantities)/5)
    report <- tibble(report = paste0(
      '<a id="quant_rp_',i , rep(1:5, n)[1:nrow(quantities)],
      '" href="#" class="action-button shiny-bound-input action_button ',
      'px-2 py-4 text-reset" onclick=get_id(this.id) ',
      'aria-live="polite"><i class="far fa-flag"></i></a>'
    ))
    
    quantities %>%
      rowwise %>%
      mutate(
        text = str_replace(
          text,
          highlight_quant(label, quantityLeast, quantityMost),
          paste0('<b>\\1</b>\\2<b>\\3</b>\\4<b>\\5</b>')
        )) %>% as_tibble %>% bind_cols(report) %>%
      select(Articles = text, Min = quantityLeast, Max = quantityMost, report) %>%
      DT::datatable(
        escape = F,
        colnames = c('Articles', 'Min', 'Max', ''),
        style = "bootstrap4",
        options = list(
          columnDefs = columnDefs,
          dom = 'tpr',
          pageLength = 5
        )) %>%
      formatStyle(c('Min','Max'), 'vertical-align'='middle') %>%
      formatStyle(c('report'), 'vertical-align'='bottom')
    
  })
}


plot_quant_qa <- function(activeqa, quantities, indexes, i){
  #' Render quantities plot
  #' activeqa: active table of answer
  #' quantities: table of quantities
  #' :return: renderPlotly
  
  id_ <- activeqa %>% pull(id) %>% .[i]
  quantities <- quantities %>% filter(id == id_)
  
  quant_active <- quantities[indexes,]
  
  renderPlotly({
    req(nrow(quant_active) > 0)
    plot_quantities(quant_active)
  })
}
