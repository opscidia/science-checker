# @copyright  Copyright (c) 2018-2021 Opscidia

read_ini <- function(filepath, encoding = getOption("encoding")) {
  #' Read ini file 
  #' filepath: str, path
  #' return: list
  #' cred: from ini package (outdated)
  
  index <- function(x, rune) {
    equalPosition = numeric(1)
    for(pos in 1:nchar(x)) {
      if (strsplit(x, '')[[1]][pos] == rune) {
        equalPosition = pos
        break
      }
    }
    return(equalPosition)
  }
  # internal helper function to find where a character occur
  
  sectionREGEXP <- '^\\s*\\[\\s*(.+?)\\s*]'
  # match section and capture section name
  
  keyValueREGEXP <- '^\\s*[^=]+=.+'
  # match "key = value" pattern
  
  ignoreREGEXP <- '^\\s*[;#]'
  # match lines with ; or # at start
  
  trim <- function(x) sub('^\\s*(.*?)\\s*$', '\\1', x)
  # amazing lack of trim at old versions of R
  
  ini <- list()
  con <- file(filepath, open = 'r', encoding = encoding)
  on.exit(close(con))
  
  while ( TRUE ) {
    
    line <- readLines(con, n = 1, encoding = encoding, warn = F)
    if ( length(line) == 0 ) {
      break
    }
    
    if ( grepl(ignoreREGEXP, line) ) {
      next
    }
    
    if ( grepl(sectionREGEXP, line) ) {
      matches <- regexec(sectionREGEXP, line)
      lastSection <- regmatches(line, matches)[[1]][2]
    }
    
    if ( grepl(keyValueREGEXP, line) ) {
      key <- trim(paste0(strsplit(line, '')[[1]][1:(index(line, '=') - 1)], collapse = ''))
      value <- trim(paste0(strsplit(line, '')[[1]][(index(line, '=') + 1):nchar(line)], collapse = ''))
      
      ini[[ lastSection ]] <- c(ini[[ lastSection ]], list(key = value))
      names(ini[[ lastSection ]])[ match('key', names(ini[[ lastSection ]])) ] <- key
    }
    
  }
  
  ini
}


is.valid <- function(x) {
  #' !is.null, !is.na, !is.nan, '"
  #' :return: bool
  is.null(need(x, message = FALSE))  
}


valueBox <- function(value, title, subtitle, icon, status){
  body <- div(class = "card-body align-self-center py-4",
    div(class = "h6 card-title mx-0 mt-2", title),
    div(class = "h2 font-weight-bold mb-0 mt-4", value),
    p(class = "mb-0 text-sm", subtitle)
  )
  icon_ <- div(class = "icon", icon)
  
  
  div(class = paste0("card col-12 card-stats mb-4 mb-xl-0 bg-", status),
    body, icon_
  )
}


cardBox <- function(
  ...,
  status = 'default',
  header = NULL,
  footer = NULL,
  class = NULL,
  header_class = NULL,
  footer_class = NULL,
  body_class = NULL
  ){
  if (is.valid(header)){
    header <- div(
      class = paste0("card-header border-", status, " ", header_class),
      header
    )}
  if (is.valid(footer)){
    footer <- div(
      class = paste0("card-footer border-", status, " ", footer_class),
      footer
    )}
  
  div(
    class = paste0("card border-", status, " ", class),
    header,
    div(class = paste("card-body p-1", body_class), ...),
    footer
  )
}



emailInput <- function(
  inputId,
  label = NULL,
  value = "",
  width = NULL,
  placeholder = NULL,
  helptext = NULL
){
  
  div(
    class = "form-group shiny-input-container",
    style = if(is.null(width)){"width:100%;"} else {paste0("width:", width, ";")},
    if(is.null(label)){NULL} else {tags$label('for' = inputId, class = "control-label", id = paste0(inputId, "-label"), label)},
    div(
      class = "input-group",
      div(
        class = "input-group-prepend",
        div(class = "input-group-text", "@")
      ),
      tags$input(
        id = inputId, class = "form-control shinyjs-resettable shiny-bound-input",
        type = "email",
        placeholder = if(is.null(placeholder)){"Enter email"} else {placeholder},
        "aria-describedby" = "emailHelp"
      )
    ),
    if(is.null(helptext)){NULL} else {tags$small(id = "emailHelp", class = "form-text text-muted", helptext)}
  )
}
