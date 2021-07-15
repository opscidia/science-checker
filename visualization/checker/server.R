library(shiny)
library(shinyjs)
library(plotly)
library(shinyThings)
library(shinyWidgets)
library(shiny.i18n)
library(promises)
library(future)
library(formattable)
library(DT)
plan(multiprocess)

shinyServer(function(input, output, session){
  
  computation <- function(
    first, second,
    relation, p_compute,
    in_corpus, in_quantities, in_scienceqa,
    signal_limit = F){
    #' Compute all indicators
    #' first, second, relation
    
    disable("check")
    disable("check_2")
    hide("corpus_plot")
    hide("sqa_render")
    hide("sqa_panel")
    
    p_compute$set(value = .1, message = i_("Creating task"))
    updateCheckboxInput(inputId = "recompute", value = F)
    updateCheckboxInput(inputId = "resulted", value = F)
    
    in_corpus <- T
    in_scienceqa <- T
    
    if(in_corpus){
      future::future({
        get_indicator(indicator = "articles",
                      first = first, second = second,
                      ci = FALSE
        )
      }) %...>% {
        corpus <- .
        if (!nrow(corpus)){
          corpus <- tibble(publication_date = character())
        }
        corpus(corpus)
      } %>% finally(~c(
        show("corpus_plot"),
        p_compute$set(value = .4, message = i_("Computing answers"))
      ))
    }
    
    if(in_scienceqa){
      future::future({
        get_indicator(indicator = "indicators",
                      first = first, second = second,
                      relation = relation,
                      pulling = "eqa", limit = limit
        )
      }) %...>% {
        response <- .
        q_ <- tibble(
          id = character(),
          quantityLeast = numeric(),
          quantityMost = numeric())
        
        quantities <- response %>% {
            if (nrow(.)){
              q <- select(., quantities) %>% 
                unnest(quantities) %>% {
                  if(nrow(.)){
                    dplyr::filter(., quantityLeast < 10) %>%
                      select(id = '_id', everything())
                  } else {
                    q_
                  }
                }
            } else {
              q_
            }
            q
          }
        
        
        scienceqa <- response %>% {
            if(nrow(.) > 0){
              select(., -quantities) %>%
              bind_cols(.$answer) %>% 
              rowwise %>% 
              mutate(
                date = substr(date, 1, 10),
                authors = clean_authors(authors),
                title = to_url(title, URL, DOI, "link-primary"),
                URL = get_url(URL, DOI),
                logit = max(c(no, yes, neutral)),
                answer = which.max(c(no, yes, neutral)),
                answer = case_when(
                  answer == 1 ~ "no",
                  answer == 2 ~ "yes",
                  TRUE ~ "neutral"
                )
              ) %>% 
              as_tibble() %>% select(
                title, authors, response, date, id = '_id', answer, logit, no, yes, neutral, URL
              ) %>% group_by(answer) %>% 
              mutate(score = n()) %>% 
              dplyr::ungroup() %>% 
              mutate(score = score*logit/100) %>% 
              dplyr::arrange(desc(score))
            } else {
              tibble(
                title = character(),
                authors = character(),
                response = character(),
                date = lubridate::Date(),
                id = character(),
                answer = character(),
                logit = double(),
                no = double(),
                yes = double(),
                neutral = double(),
                URL = character(),
                score = numeric()
              )
            }
          }
          
        
        if (signal_limit & nrow(scienceqa) > limit){
          complete_limit(TRUE)
        } else {
          complete_limit(FALSE)
        }
        
        scienceqa(scienceqa)
        filterqa(scienceqa)
        quantities(quantities)
        
        return(T)
        
      } %>% then(
        onFulfilled = function(response){
          updateCheckboxInput(inputId = "resulted", value = (nrow(scienceqa()) > 0))
        },
        onRejected = function(e){
          showNotification("No results", duration = 5, type = "error")
        }
      ) %>% finally(~c(
        itemsqa(nrow(scienceqa())),
        enable('check'), enable('check_2'),
        show('sqa_render'), show('sqa_panel'),
        updateCheckboxInput(inputId = "computed", value = T),
        updateCheckboxInput(inputId = "recompute", value = T),
        p_compute$set(value = 1, message = i_("Task completed")),
        showNotification(i_("Task completed"), duration = 5, type = "message"),
        p_compute$close()
      ))
    }
    
    return(NULL)
  }
  
  
  output$controller <- renderUI({
    req(!PROD)
    dropdownButton(
      materialSwitch(
        inputId = "in_corpus",
        label = "corpus", 
        value = TRUE,
        right = TRUE,
        status = "primary"
      ),
      materialSwitch(
        inputId = "in_quantities",
        label = "quantities", 
        value = TRUE,
        right = TRUE,
        status = "primary"
      ),
      materialSwitch(
        inputId = "in_scienceqa",
        label = "answers", 
        value = TRUE,
        right = TRUE,
        status = "primary"
      ),
      circle = TRUE, status = "primary",
      icon = icon("gear"), width = "300px",
      tooltip = tooltipOptions(title = "Control indicators")
    )
  })
  
  observe({
    hide("computed")
    hide("recompute")
    hide("resulted")
  })
  
  
  observe({
    # Switch Language by URL
    query <- parseQueryString(session$clientData$url_search)
    lang <- query[['lang']]
    
    req(lang%in%c('en', 'fr'))
    
    s_lang <- isolate(input$s_lang)
    if (s_lang != lang){
      updateSelectInput(session, 's_lang', selected = lang)
    }
  })
  
  
  observeEvent(input$s_lang, {
    # Switch Language by input
    shiny.i18n::update_lang(session, input$s_lang)
    
    query <- parseQueryString(session$clientData$url_search)
    lang <- query[['lang']]
    
    req(lang%in%c('en', 'fr'))
    s_lang <- isolate(input$s_lang)
    
    if (s_lang != lang){
      updateQueryString(paste0("?lang=", input$s_lang), 'push', session)
    }
  })
  
  
  output$title <- renderUI({
    query <- parseQueryString(session$clientData$url_search)
    q_lang <- query[['lang']]
    s_lang <- input$s_lang
    
    lang <- if(is.valid(q_lang)){q_lang}else{s_lang}
    
    a(href = paste0('/?lang=', lang), "Science Checker")
  })
  
  
  observe({
    complete <- reactiveValuesToList(input) %>% 
      .[c('first', 'second')] %>% 
      sapply(is.valid) %>% all
    if(complete){enable("check")}else{disable("check")}
  })
  
  observe({
    complete <- reactiveValuesToList(input) %>% 
      .[c('first_2', 'second_2')] %>% 
      sapply(is.valid) %>% all
    if(complete){enable("check_2")}else{disable("check_2")}
  })
  
  session <- session
  corpus <- reactiveVal()
  quantities <- reactiveVal()
  scienceqa <- reactiveVal()
  filterqa <- reactiveVal()
  itemsqa <- reactiveVal()
  complete_limit <- reactiveVal(FALSE)
  keywords <- reactiveValues()
  
  observeEvent(input$check, {
    
    first <- isolate(input$first)
    second <- isolate(input$second)
    relation <- isolate(input$relation)
    p_compute <- Progress$new(session = session)
    
    keywords$first <- first
    keywords$second <- second
    keywords$relation <- relation
    
    updateCheckboxInput(inputId = "computed", value = T)
    updateCheckboxInput(inputId = "recompute", value = F)
    updateTextInput(session = session, inputId = "first_2", value = first)
    updateTextInput(session = session, inputId = "second_2", value = second)
    updateSelectInput(session = session, inputId = "relation_2", selected = relation)
    
    in_corpus <- input$in_corpus %>% is.valid
    in_quantities <- input$in_quantities %>% is.valid
    in_scienceqa <- input$in_scienceqa %>% is.valid
    if(PROD){
      in_corpus <- T
      in_quantities <- T
      in_scienceqa <- T
    }

    computation(
      first, second,
      relation, p_compute,
      in_corpus, in_quantities, in_scienceqa,
      TRUE
    )
    
    return(NULL)
  })
  
  
  observeEvent(input$check_2, {
    
    # updateCheckboxInput(inputId = "computed", value = F)
    updateCheckboxInput(inputId = "recompute", value = F)
    
    first <- isolate(input$first_2)
    second <- isolate(input$second_2)
    relation <- isolate(input$relation_2)
    p_compute <- Progress$new(session = session)
    
    keywords$first <- first
    keywords$second <- second
    keywords$relation <- relation
    
    in_corpus <- input$in_corpus %>% is.valid
    in_quantities <- input$in_quantities %>% is.valid
    in_scienceqa <- input$in_scienceqa %>% is.valid
    if(PROD){
      in_corpus <- T
      in_quantities <- T
      in_scienceqa <- T
    }
    
    computation(
      first, second,
      relation, p_compute,
      in_corpus, in_quantities, in_scienceqa,
      TRUE
    )
    
    return(NULL)
  })
  
  
  ##########################################################################
  ######################    CORPUS    ######################################
  ##########################################################################
  
  output$corpus_plot <- renderPlotly({
    req(corpus())
    req(nrow(corpus()))
    plot_corpus(corpus())
  })
  
  output$corpus_stat <- renderUI({
    req(corpus())
    first <- isolate(keywords$first)
    second <- isolate(keywords$second)
    stat <- corpus() %>% nrow %>%
      format(big.mark = ' ')
    
    paste0('<strong>', stat,
           '</strong> ', i_('Open Acess articles related to'), ' "',
           first, '" ', i_('and'), ' "', second, '".') %>% shiny::HTML() %>% h5()
  })
  
  output$corpus_art <- renderDataTable({
    req(corpus())
    
    columnDefs <- list(
      #Relevance
      list(targets = 0, visible = F),
      #Articles
      list(targets = 1, orderData = 2, searchable = T),
      #Date
      list(targets = 2, visible = F)
    )
    
    corpus() %>% 
      select(title, URL, DOI, authors, date = publication_date) %>% 
      rowwise %>% 
      mutate(
        authors = clean_authors(authors),
        title = paste0(
          to_url(title, URL, DOI, "font-weight-bold"),
          '<br><span class="font-weight-light">',
          date, '  |  ', authors, '</span>')
      ) %>% as_tibble %>%  select(Articles=title, date) %>% 
      DT::datatable(
        escape = F,
        style = "bootstrap4",
        options = list(
          columnDefs = columnDefs,
          lengthMenu = c(5, 10),
          autoWidth = T,
          scrollX = T
      ))
  })
  
  
  
  ##########################################################################
  ####################      ANSWERS     ####################################
  ##########################################################################
  
  observeEvent(input$check_all, {
    first <- isolate(keywords$first)
    second <- isolate(keywords$second)
    relation <- isolate(keywords$relation)
    
    body <- div(
      class = "container px-3",
      p(class = "text-center",
        strong("Does", first, relation, second, "?")
      ),
      p(class = "text-center",
        i_("Computing all the answers may take some time. We will notify you by email when it is completed.")
      ),
      emailInput(
        inputId = "email_all",
        placeholder = "your@email.com",
        helptext = i_("We'll never share your email with anyone else.")
      )
    )
    
    showModal(modalDialog(
      body,
      title = i_("Compute all answers"),
      footer = div(
        actionButton("cancel", i_("Cancel"),
                     class = "btn btn-light", "data-dismiss" = "modal"),
        actionButton("get_all", i_("Check"))
      ),
      size = "m"
    ), session = session)
    
  })
  
  observeEvent(input$get_all, {
    first <- isolate(keywords$first)
    second <- isolate(keywords$second)
    relation <- isolate(keywords$relation)
    email <- isolate(input$email_all)
    
    disable("get_all")
    disable("check_all")
    
    future::future({
      get_indicator(indicator = "indicators/all/",
                    first = first, second = second,
                    relation = relation,
                    pulling = "eqa",
                    email = email
      )
    })
    
    removeModal(session)
    showNotification(
      i_("Task has been created."),
      duration = 10, type = "message")
    
    return(NULL)
  })
  
  
  paged <- reactiveVal(1)
  observeEvent(input$recheck, {
    actual_sqa <- isolate(scienceqa())
    actual_q <- isolate(quantities())
    page <- isolate(paged())+1 
    first <- isolate(keywords$first)
    second <- isolate(keywords$second)
    relation <- isolate(keywords$relation)
    p_compute <- Progress$new(session = session)
    
    disable("check")
    disable("check_2")
    disable("recheck")
    
    p_compute$set(value = .5, message = i_("Computing answers"))
    

    future::future({
      get_indicator(indicator = "indicators",
                    first = first, second = second,
                    relation = relation,
                    pulling = "eqa", limit = limit,
                    page = page
      )
    }) %...>% {
      response <- .
      
      quantities <- response %>% 
        select(quantities) %>% 
        unnest(quantities) %>% {
          if (nrow(.)){
            q <- dplyr::filter(., quantityLeast < 10) %>%
              select(id = '_id', everything())
            
          } else {
            q <- tibble(
              id = character(),
              quantityLeast = numeric(),
              quantityMost = numeric())
          }
          q
        }
      
      if (is.valid(response)){
        scienceqa <- response %>% 
          select(-quantities) %>%
          bind_cols(.$answer) %>% 
          rowwise %>% 
          mutate(
            authors = clean_authors(authors),
            title = to_url(title, URL, DOI, "link-primary"),
            URL = get_url(URL, DOI),
            logit = max(c(no, yes, neutral)),
            answer = which.max(c(no, yes, neutral)),
            answer = case_when(
              answer == 1 ~ "no",
              answer == 2 ~ "yes",
              TRUE ~ "neutral"
            )
          ) %>% 
          as_tibble() %>% select(
            title, authors, response, date, id = '_id', answer, logit, no, yes, neutral, URL
          ) %>% group_by(answer) %>% 
          mutate(score = n()) %>% 
          dplyr::ungroup() %>% 
          mutate(score = score*logit/100)
      }
      
      if (nrow(scienceqa) == 0){
        complete_limit(TRUE)
      }
      
      bind_rows(actual_sqa, scienceqa) %>% unique %>%  dplyr::arrange(desc(score)) -> scienceqa
      bind_rows(actual_q, quantities) %>% unique -> quantities
      
      scienceqa(scienceqa)
      filterqa(scienceqa)
      quantities(quantities)
      
    } %>% finally(~c(
      enable("recheck"),
      enable('check_2'),
      paged(page),
      itemsqa(nrow(scienceqa())),
      p_compute$set(value = 1, message = i_("Task completed")),
      showNotification(i_("Task completed"), duration = 5, type = "message"),
      p_compute$close()
    ))
    
    return(NULL)
    
  })
  
  pagelength <- reactive({
    req(corpus())
    req(nrow(corpus()))
    nrow(corpus())%/%limit
  })
  
  
  sqa_summary <- reactive({
    req(scienceqa())
    req(nrow(scienceqa()) > 0)
    scienceqa() %>% 
      group_by(answer) %>% 
      summarise(
        confidence = mean(logit),
        response = n()*100/nrow(.)
      ) %>% as_tibble
  })
  
  
  output$sqa_plot <- renderPlot({
    req(sqa_summary())
    req(nrow(sqa_summary()))
    sqa_summary() %>% 
      select(response, answer) %>% 
      spread(answer, response) %>% 
      sqa_subplot(s=12, t=5) +
      theme(
        axis.text = element_text(size = rel(1.3))
      )
  })
  
  
  output$sqa_data <- renderFormattable({
    req(sqa_summary())
    req(nrow(sqa_summary()))
    sqa_summary() %>% 
      mutate_if(is.double, function(x) percent(x/100)) %>% 
      mutate(answer = case_when(
        answer == 'yes' ~ i_('Affirmative'),
        answer == 'no' ~ i_('Negative'),
        T ~ 'Neutral')) %>% 
      dplyr::arrange(answer) %>% 
      select(Answer = answer, Response = response, " " = response, Confidence = confidence) %>% 
      formattable(list(
        Confidence = formatter("span", style = x ~ formattable::style(
          display = 'inline-block',
          width = "90%",
          "text-align" = "center",
          "border-radius" = "30px",
          "padding" = ".2em .5em",
          "white-space" = "nowrap",
          "font-weight" = "bolder",
          "background-color" = bicss(c(x), '#fce5b6', hue$warning)
        )),
        Response = formatter("span", style = x ~ formattable::style(
          display = 'inline-block',
          "background-color" = ifelse(.$Answer == i_('Affirmative'), hue$green, ifelse(.$Answer == i_('Negative'), hue$danger, hue$grey)),
          color = "transparent",
          # color = ifelse(.$Answer == i_('Affirmative'), hue$dark_blue, ifelse(.$Answer == i_('Negative'), hue$white, hue$dark_blue)),
          "border-radius" = "15px",
          "white-space" = "nowrap",
          width = x
        )),
        " " = formatter("span", style = x ~ formattable::style(
          display = "inline-block",
          padding = ".2em .5em .2em .2em",
          background = bicss(c(x), hue$grey, hue$warning),
          "max-height" = "25px",
          "border-radius" = "0 30px 30px 0",
          "font-weight" = "bolder",
          width = "100%"
        ))
      ), align = c('l', 'l', 'c', 'r')
      )
  })
  
  
  output$sqa_panel <- renderUI({
    req(sqa_summary())
    req(nrow(sqa_summary()) > 0)
    
    balance <- balanced(sqa_summary())
    
    decision <- sqa_summary() %>%
      mutate(decision = response*confidence/100) %>% 
      dplyr::arrange(desc(decision)) %>% .[1,]
    
    if (balance$balanced & decision$answer != 'neutral') {
      value <- i_('Balanced')
      status <- "info text-white"
      icon_ <- 'dot-circle'
      subtitle <- i_("This issue is being discussed")
      #subtitle <- paste(i_('With a z-value of'), sprintf("%0.2f", balance$z))
      
    } else {
      if (decision$answer == 'yes'){
        value <- i_("Affirmative")
        status <- "secondary"
        icon_ <- "check-circle"
      } else if (decision$answer == 'no'){
        value <- i_("Negative")
        status <- "danger text-white"
        icon_ <- "times-circle"
      } else {
        value <- i_("Neutral")
        status <- "info text-white"
        icon_ <- "dot-circle"
      }
      confidence <- decision$confidence %>%
        round(2) %>% paste("%")
      
      subtitle <- paste(i_("With"), confidence, i_("confidence."))
    }
    
    final_decision <- valueBox(
      value = value,
      subtitle = subtitle,
      title = i_("Final Decision"),
      icon = icon(icon_),
      status = status
    )
    
    q_sqa <- h5(
      class = 'text-center',
      "Does", keywords$first, keywords$relation, keywords$second, "?"
    )
    
    n_sqa <- h5(class = 'text-center pb-3',
      strong(nrow(scienceqa()), i_("answers")),
      i_("found in our Open access database"),
      br(),{
        if (nrow(quantities())){
          paste(i_("including"), nrow(quantities()), i_("numerical answers"))
        } else {
          i_("with no numerical answer")
        }
      }
    )
    
    miss <- if(complete_limit()) {FALSE} else {nrow(scienceqa()) < nrow(corpus())}
    
    info_next <- paste(i_("Answers are computed from"), "<b>", i_("the first"),
      nrow(scienceqa()), i_("relevant articles only"), "</b>", i_("on total of"),
      nrow(corpus()), "articles."
    ) %>% shiny::HTML()
    if (is.valid(pagelength())){
      info_next <- div(
        info_next,
        if (miss) {p(
          i_("Click 'Add' to append the next"), limit, "articles",
          ",", i_("'All' to compute the ensemble.")
        )} else {NULL},
        if (miss) {actionButton("recheck", i_("Add"), icon("plus"))} else {NULL},
        if (miss) {actionButton("check_all", i_("All"), icon("hourglass-start"))} else {NULL}
      )
    }
    
    tagList(
      q_sqa, n_sqa,
      fluidRow(
        column(3,
          class = "d-flex",
          final_decision
          ),
        column(6,
          class = "d-flex",
          cardBox(
            status = "grey",
            class = "col-12 px-0 mb-4 mb-xl-0 bg-grey align-items-center",
            body_class = "px-3 col-12 row align-items-center",
            formattableOutput("sqa_data")
          )),
        column(3,
          class = "d-flex",
          cardBox(
            status = "grey",
            class = "col-12 mb-4 mb-xl-0 bg-grey p-2 text-center",
            info_next
          )
          )
      )) %>% withSpinner()
  })
  
  
  output$sqa_filter <- renderUI({
    req(scienceqa())
    req(nrow(scienceqa()) > 0)
    
    dates <- scienceqa() %>% 
      mutate(date = as.numeric(format(as.Date(date), "%Y"))) %>% pull(date)
    
    div(
      id = "filters_parent",
      class = "card my-3",
      div(
        class = "card-header",
        id = "filters",
        div(
          class = "mb-0 px-3 d-flex justify-content-between",
          tags$button(
            class = "btn btn-link btn-block btn-outline-none px-0 py-0 text-decoration-none",
            "data-toggle" = "collapse",
            "data-target" = "#filters_body",
            "aria-expanded" = "true",
            "aria-controls" = "filters_body",
            p(class = "my-0 lead text-primary font-weight-bolder text-left", i_("Advanced"))
          ),
          p(class = "my-0 lead text-primary font-weight-bolder text-left", tags$i(class = "fas fa-sort-amount-down"))
        )
      ),
      div(
        id = "filters_body",
        class = "collapse",
        "aria-labelledby" = "filters",
        "data-parent" = "#filters_parent",
        div(
          class = "card-body",
          fluidRow(
            class = "container m-0",
            column(
              6,
              p(
                class = "mb-1 lead text-primary font-weight-bolder text-left",
                i_("Filters")
              ),
              checkboxGroupButtons(
                "filter_only",
                i_("Show only articles with"),
                choiceValues = c("Quantities", "FullText", "Affirmative", "Negative", "Neutral"),
                choiceNames = c(i_("Numerical conclusions"), i_("Full Text"), i_("Affirmative"), i_("Negative"), i_("Neutral")),
                status = "primary",
                justified = T,
                individual = T,
                width = "100%"
              ),
              airYearpickerInput(
                inputId = "filter_dates",
                label = i_("Year Range"),
                value = c(min(dates), max(dates)) %>% paste0("-01-01"),
                placeholder = "since always",
                separator = " to ",
                update_on = "change",
                addon = "left",
                minDate = min(dates) %>% paste0("-01-01"),
                maxDate = max(dates) %>% paste0("-01-01"),
                clearButton = T,
                range = T,
                autoClose = T
              )
            ),
            column(
              6,
              class = "d-flex flex-column justify-content-between",
              div(
                p(class = "mb-1 lead text-primary font-weight-bolder text-left", i_("Sorting")),
                pickerInput(
                  "sorting",
                  i_("Sort by"), 
                  choices = c(
                    "Date" = "recency",
                    "Date " = "recency_desc",
                    "Score" = "confidence",
                    "Score " = "confidence_desc"
                  ),
                  selected = "confidence_desc",
                  choicesOpt = list(icon = c(
                    "fas fa-arrow-up",
                    "fas fa-arrow-down",
                    "fas fa-arrow-up",
                    "fas fa-arrow-down"
                  ))
              )),
              div(
               class = "d-flex justify-content-center justify-content-md-end",
               actionButton(
                 "filter_apply",
                 i_("Apply"),
                 icon = icon("filter")
               ),
               span(class = "px-1"),
               actionButton(
                 "filter_reset",
                 i_("Reset"),
                 status = "light",
                 class = "btn-light"
               )
              )
            )
          )
        )
      )
    )
  })
  
  pager_index <- reactive({
    req(scienceqa())
    shinyThings::pager('pager', nrow(filterqa()), 5)
  })
  
  activeqa <- reactive({
    req(pager_index()())
    indexes <- pager_index()()
    filterqa()[indexes,] %>% 
      mutate(y = 1:n())
  })
  
  observe({
    req(activeqa())
    
    
    lapply(1:5, function(i) {
      output[[paste0('out_', i)]] <- activeqa() %>% 
        select(no, yes, neutral) %>% .[i,] %>% sqa_subtable()
    })
    
    
    lapply(1:5, function(i) {
      output[[paste0('quant_art_', i)]] <- table_quant_qa(activeqa(), quantities(), i)
    })
    
  })
  
  observe({
    lapply(1:5, function(i) {
      indexes <- input[[paste0('quant_art_', i, '_rows_current')]]
      output[[paste0('quant_plot_', i)]] <- plot_quant_qa(activeqa(), quantities(), indexes, i)
    })
  })
  
  output$sqa_render <- renderUI({
    req(filterqa(), quantities())
    
    if(nrow(filterqa())){
      req(activeqa())
      out <- activeqa() %>% 
        select(y, title, authors, response, date, id, URL) %>% 
        apply(1, format_sqa, quantities = quantities()) %>% 
        div(class = "container")
    } else {
      out <- div(
        class = "container",
        h3(
          class = "text-center text-light my-5 py-5",
          i_("No results match the applied filters.")
        )
      )
    }
    
    out
    
  })
  
  
  observeEvent(input$filter_apply, {
    # Apply ordering
    
    
    filterqa <- isolate(scienceqa())
    
    dates <- filterqa %>% 
      mutate(date = as.numeric(format(as.Date(date), "%Y"))) %>% pull(date)
    
    f_only <- isolate(input$filter_only)
    f_dates <- isolate(input$filter_dates)
    f_dates <- case_when(
      !is.valid(f_dates[2]) & length(f_dates) > 0 ~ c(format(f_dates[1], "%Y") %>% paste0("-01-01"), format(f_dates[1], "%Y") %>% paste0("-12-31")),
      !is.valid(f_dates) ~ c(min(dates) %>% paste0("-01-01"), max(dates) %>% paste0("-12-31")),
      T ~ if(is.valid(f_dates)){as.character(f_dates)}else{c("1800-01-01", "2020-12-31")}
    )
    sorting <- isolate(input$sorting)
    ans <- c('yes', 'no', 'neutral')[which(c('Affirmative', 'Negative', 'Neutral')%in%f_only)]
    ans <- if(is.valid(ans)){ans}else{c('yes', 'no', 'neutral')}
    
    if ('Quantities'%in%f_only){
      filterqa <- filter(filterqa, id%in%(quantities() %>% pull(id)))
    }
    if ('FullText'%in%f_only){
      filterqa <- filter(filterqa, !is.na(URL))
    }
    filterqa <- filterqa %>% 
      filter(
        between(
          as.numeric(as.Date(date)),
          as.numeric(as.Date(f_dates[1])),
          as.numeric(as.Date(f_dates[2]))
        ),
        answer%in%ans
      )
    
    filterqa <- filterqa %>% {
      if(sorting == "recency"){
        arrange(., desc(date))
      } else if (sorting == "recency_desc"){
        arrange(., date)
      } else if (sorting == "confidence"){
        arrange(., score)
      } else {
        arrange(., desc(score))
      }
    }
    
    filterqa(filterqa)
    
    showNotification(
      i_("Ordering applied."),
      duration = 5, type = "default")
  })
  
  
  observeEvent(input$filter_reset, {
    # Reset Ordering
    
    dates <- scienceqa() %>% 
      mutate(date = as.numeric(format(as.Date(date), "%Y"))) %>% pull(date)
    
    updateCheckboxGroupButtons(session, "filter_only", selected = "")
    updateAirDateInput(session, "filter_dates", clear = T)
    updatePickerInput(session, "sorting", selected = NULL)
    
    filterqa(isolate(scienceqa()) %>% as_tibble)
    
    showNotification(
      i_("Ordering reseted."),
      duration = 5, type = "default")
    
  })
  
  

  ##########################################################################
  ####################      REPORTS     ####################################
  ##########################################################################
  
  observeEvent(input$report_id,{
    #' Modal report
    
    report_id <- isolate(input$report_id)
    i <- report_id %>% str_extract("[0-9]+") %>% 
      as.integer()
    first <- isolate(keywords$first)
    second <- isolate(keywords$second)
    relation <- isolate(keywords$relation)
    if (report_id %>% startsWith("quant")){
      # Report Quantities

      j <- substr(i, 1, 1) %>% as.integer()
      i <- substr(i, 2, 2) %>% as.integer()
      
      id_ <- activeqa() %>% pull(id) %>% .[j]
      quantities <- quantities() %>% filter(id == id_)
      
      row_ <- quantities[i,]
      body <- div(
        class = "container-fluid px-3",
        p(class = "text-center",
          i_("Thank you for helping us to improve the Science checker project Quantities indicator. You can correct the following values for this data.")
        ),
        textAreaInput(
          inputId = "quant_rp_text", label = strong(i_("Text")),
          value = row_$text, width = "100%", rows = 5,
          resize = 'none'
        ),
        textInput(
          inputId = "quant_rp_label", label = strong("Label"),
          value = row_$label, width = "100%"
        ),
        fluidRow(
          column(6,
            numericInput(
              inputId = "quant_rp_min",
              label = strong("Min value"),
              value = row_$quantityLeast,
              step = 0.01)),
          column(6,
            numericInput(
              inputId = "quant_rp_max",
              label = strong("Max value"),
              value = row_$quantityMost,
              step = 0.01))
        )
      )
    } else if (report_id %>% startsWith("sqa")){
      # Report Answer

      row_ <- as_tibble(activeqa())[i,]
      hg <- row_$response %>%
        str_match_all('<span class="hg">(.*?)<\\/span>') %>%
        do.call(rbind, .) %>% .[,2] %>% paste(collapse = ' ; ')
      body <- div(
        class = "container-fluid px-3",
        p(class = "text-center",
          i_("Thank you for helping us to improve the Science checker project Answers indicator. You can correct the following values for this data.")
        ),
        cardBox(
          class = 'bg-grey mb-3', status = 'grey',
          p(
            class = "m-0 px-1",
            strong("Question: "), paste('Does', first, relation, second, '?'),
            br(class = "mb-2"),
            strong("Article: "), HTML(row_$title), br(),
            span(class = 'pl-4', row_$authors), br(),
            span(class = 'text-muted pl-4', row_$date)
        )),
        textAreaInput(
          inputId = "sqa_rp_hg",
          label = p(class = "m-0 p-0",
                    strong("Highlights"),
                    tags$small(i_("(separated by semicolon ; )"))),
          value = hg, width = "100%", rows = 8, resize = 'none'
        ),
        selectInput(
          inputId = "sqa_rp_decision",
          label = strong(i_("Final Decision")),
          selected = row_$answer,
          choices = c('yes', 'no', 'neutral')
        ),
        textAreaInput(
          inputId = "sqa_rp_add",
          label = '', width = "100%", resize = 'none',
          placeholder = i_("Additional information")
        )
      )
    }
    
    showModal(modalDialog(
      body,
      title = i_("Report an issue"),
      footer = div(
        actionButton("cancel", i_("Cancel"),
          class = "btn btn-light", "data-dismiss" = "modal"),
        actionButton("report", i_("Send Report"))
        ),
      size = "m"
    ), session = session)
    
  })
  
  
  observeEvent(input$report,{
    #' Log report
    
    report_id <- isolate(input$report_id)
    first <- isolate(keywords$first)
    second <- isolate(keywords$second)
    relation <- isolate(keywords$relation)
    if (report_id %>% startsWith("quant")){
      # Quantities logs
      
      tibble(
        first = first, second = second, relation = relation,
        timestamp = Sys.time(),
        text = isolate(input$quant_rp_text),
        label = isolate(input$quant_rp_isolate),
        min = isolate(input$quant_rp_min),
        max = isolate(input$quant_rp_max)
      ) %>% write_csv(
        path = quant_log,
        append = file.exists(quant_log))
      
    } else if (report_id %>% startsWith("sqa")){
      # Answers logs
      row_ <- as_tibble(activeqa())[report_id %>%
                                      str_extract("[0-9]+") %>%
                                      as.integer(),] %>% isolate()
      tibble(
        first = first, second = second, relation = relation,
        timestamp = Sys.time(),
        text = row_$response,
        highlights = isolate(input$sqa_rp_hg),
        decision = isolate(input$sqa_rp_decision),
        additional = isolate(input$sqa_rp_add)
      ) %>% write_csv(
        path = sqa_log,
        append = file.exists(sqa_log))
    }
    
    removeModal(session)
    showNotification(
      i_("Your contribution has been acknowledged."),
      duration = 5, type = "message")
  })
  
  
})