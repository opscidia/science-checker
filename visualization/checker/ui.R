library(shiny)
library(shiny.i18n)
library(shinycssloaders)
library(shinyThings)
library(shinyjs)
library(plotly)


shinyUI(bootstrapPage(
    title = "Science Checker | Opscidia",
    theme = theme,
    tags$head(includeHTML("www/head.html")),
    useShinyjs(),
    shiny.i18n::usei18n(i18n),
    includeCSS("www/main.css"),
    includeScript("www/script.js"),
    div(class = "container-fluid p-0 m-0",
    div(class = "d-none",
      checkboxInput("computed", NULL, F, "0px"),
      checkboxInput("recompute", NULL, F, "0px"),
      checkboxInput("resulted", NULL, F, "0px")
    ),
    conditionalPanel(
      class = "noaction p-0 m-0",
      condition = "input.computed == 0",
      div(class = "container-fluid p-0 m-0 top",
        h1(class = "text-center my-4 py-1 text-darkblue", "Science Checker"),
        div(class = "px-md-5 container d-flex justify-content-center",
          div(class = "card shadow-lg px-3 py-4 py-md-5 col-md-10",
            h3(class = "text-center mt-0 mb-4", i_("What does the research literature say about it ?")),
            fluidRow(class = "justify-content-center",
                     column(3,
                       class = "px-md-2",
                       textInput("first", i_('Enter an agent'), '', "100%", "vaccine,  sugar")),
                     column(3,
                       class = "px-md-2",
                       selectInput("relation", i_('Select an effect'), c("increase", "cause", "prevent", "cure"), width = "100%")),
                     column(3,
                       class = "px-md-2",
                       textInput("second", i_('Enter a disease'), '', "100%", "headache,  cancer"))
            ),
            fluidRow(class = "text-light justify-content-center",
                     actionButton("check", i_("Check"), icon('search'), class = "px-4")
            )
          )
        )
      ),
      div(class = "bg-white",
        div(class = "container-fluid bg-wg-50",
          div(class = "container py-5",
            h3(class = "text-center mt-0", i_("What are the goals of Science Checker?")),
            fluidRow(class = "px-md-5 mx-md-5 py-3",
              column(4, class = "mb-3 mb-sm-0 px-4 px-md-1 px-lg-3",
                div(class = "card card-shadow h-100 p-3 position-relative",
                  img(
                    class = "mx-auto d-block mw-100",
                    src = "https://www.opscidia.com/wp-content/uploads/2019/05/rd.png",
                    width = "150px"
                  ),
                  h5(class = "text-center", i_("Explore the scientific literature")),
                  p(class = "text-center",
                    i_("Useful for science journalists and the curious")
                  )
                )
              ),
              column(4, class = "mb-3 mb-sm-0 px-4 px-md-1 px-lg-3",
                div(class = "card card-shadow h-100 p-3 position-relative",
                  img(
                    class = "mx-auto d-block mw-100",
                    src = "https://www.opscidia.com/wp-content/uploads/2019/05/journal.png",
                    width = "150px"
                  ),
                  h5(class = "text-center", i_("Understand the established scientific consensus")),
                  p(class = "text-center",
                    i_("It is therefore necessary to analyze several studies, not just one")
                  )
                )
              ),
              column(4, class = "mb-3 mb-sm-0 px-4 px-md-1 px-lg-3",
                div(class = "card card-shadow h-100 p-3 position-relative",
                  img(
                    class = "mx-auto d-block mw-100",
                    src = "https://www.opscidia.com/wp-content/uploads/2019/05/open_access.png",
                    width = "150px"
                  ),
                  h5(class = "text-center", i_("Demonstrate the usefulness of Open Access")),
                  p(class = "text-center",
                    i_("Like Open Source, we see Open Access as a high-value issue")
                  )
                )
              )
            )
          )
        ),
        div(class = "container-fluid bg-gw-25",
          div(class = "container pb-5",
            h3(class = "text-center mt-0", i_("What is Science Checker?")),
            fluidRow(class = "px-md-5 mx-md-5 py-3",
              column(4, class = "mb-3 mb-sm-0 px-4 px-md-1 px-lg-3 d-flex align-items-center",
                div(class = "card w-100 h-180px p-3 position-relative border-blue border-2 border-h-green",
                  p(class = "lead text-center font-weight-bold text-primary mt-3", i_("Your question")),
                  p(class = "text-center position-absolute bottom-0 right-0 mb-4 mb-md-5 px-4 px-lg-5",
                    i_("In the field of health about a"),
                    strong(i_("link")),
                    i_("between an"), strong(i_("agent")),
                    i_("and a"), strong(i_("disease"))
                  )
                )
              ),
              column(4, class = "mb-3 mb-sm-0 px-4 px-md-1 px-lg-3",
                div(class = "card h-100 p-3 position-relative border-blue border-2 border-h-green",
                  p(class = "text-center",
                    i_("The AI will"),
                    strong(i_("study the database")),
                    i_("to discover the"),
                    strong(i_("scientific consensus")),
                    i_("on the health topic concerned by your query")
                  ),
                  img(
                    class = "mx-auto d-block mw-100",
                    src = "mr_robot.png"
                  ),
                  p(class = "text-center",
                    i_("And will then"),
                    strong(i_("deduce an answer")),
                    i_("by proposing the"),
                    strong(i_("most relevant articles")),
                    i_("that can answer it")
                  )
                )
              ),
              column(4, class = "mb-3 mb-sm-0 px-4 px-md-1 px-lg-3 d-flex align-items-center",
                div(class = "card w-100 h-180px p-3 position-relative border-blue border-2 border-h-green",
                  p(class = "lead text-center font-weight-bold text-primary mt-3", i_("Data base")),
                  p(class = "text-center position-absolute bottom-0 right-0 mb-4 mb-sm-5 px-4",
                    i_("3 million articles in Open Access from"),
                    strong("PubMed"),
                    i_("(among 36 million) used as a"),
                    strong(i_("source of information"))
                  )
                )
              )
            )
          )
        ),
        div(class = "container-fluid",
          div(class = "container pb-5",
            h3(class = "text-center mt-0", i_("How to participate in the development of the project?")),
            div(class = "px-md-5 mx-md-5 py-3",
              div(class = "row",
                div(class = "col col-md-7 pr-lg-5",
                  h4(i_("As a Science Checker user:")),
                  p(class = "pr-lg-5",
                    i_("It is possible for you to give us feedback using the"),
                    span(class = "text-primary",
                      tags$i(class = "fa fa-flag", role = "presentation", "aria-label" = "flag icon"),
                      i_("Report")
                    ),
                    i_("button or the"),
                    tags$i(class = "far fa-flag px-1"), i_("odds ratio flag"),
                    i_("if an answer seems incorrect or for any other potential error.")
                  )
                )
              ),
              div(class = "row",
                div(class = "col col-md-7 offset-md-5",
                  h4(class = "text-md-right",
                    i_("As a professional:")
                  ),
                  p(class = "text-md-right",
                    i_("We are looking for funding and are open to technological partnerships to develop the tool. So if you are interested and want to support us, please contact us at"),
                    a(href = "mailto:contact@opscidia.com?subject=Science Checker", target = "_blank", "contact@opscidia.com"),
                    i_("or via the contact form available"),
                    a(href = "https://www.opscidia.com/contact/", target = "_blank", i_("here"))
                  )
                )
              )
            )
          )
        ),
        div(class = "container-fluid bg-grey-soft",
          div(class = "container pt-2 pb-3",
            div(class = "row justify-content-md-center pt-4",
              div(class = "col-10 col-md-5 col-lg-3", img(src = "vietsch.svg", width = "100%"))
            ),
            div(class = "px-md-5 mx-md-5 py-3",
              h5(class = "text-center font-weight-normal font-family-base px-md-5",
              i_("We would especially like to thank the Vietsch Foundation for funding the project, as well as for its follow-up and the enriching exchanges we had during its development.")
              )
            )
          )
        ),
        div(class = "container-fluid",
          div(class = "container",
            div(class = "row justify-content-center py-3",
              div(class = "h5 font-weight-normal col col-md-10 col-lg-6",
                p(class = "text-center",
                  i_("Science Checker does not provide medical or health advice and is not intended for self-medication. Search results may contain outdated or inaccurate information.")
                ),
                p(class = "text-center",
                  strong(i_("Only a healthcare professional can provide medical advice."))
                )
              )
            )
          )
        )
      )
    ), 
    conditionalPanel(
      class = "doaction p-0 m-0",
      condition = "input.computed == 1",
      div(class = "container-fluid p-0 m-0",
          h1(class = "text-center my-4 py-1 text-darkblue", uiOutput('title', inline = T)),
          div(class = "container-fluid position-absolute top",
            div(class = "container px-0 px-md-5",
              div(class = "card-control bg-white col-12 col-md-10 offset-md-1 border border-light rounded-top",
                style = "height:520px;")
            )
          ),
          div(class = "container d-flex justify-content-center px-md-5",
              div(class = "px-3 py-4 py-md-5 col-md-10",
                  h3(class = "text-center mt-0 mb-4", i_("What does the research literature say about it ?")),
                  fluidRow(class = "justify-content-center",
                           column(3,
                                  class = "px-md-2",
                                  textInput("first_2", i_('Enter an agent'), '', "100%", "vaccine,  sugar")),
                           column(3,
                                  class = "px-md-2",
                                  selectInput("relation_2", i_('Select an effect'), c("increase", "cause", "prevent", "cure"), width = "100%")),
                           column(3,
                                  class = "px-md-2",
                                  textInput("second_2", i_('Enter a disease'), '', "100%", "headache,  cancer"))
                  ),
                  fluidRow(class = "text-light justify-content-center",
                           actionButton("check_2", i_("Check"), icon('search'), class = "px-4")
                  )
              )
          )
      ),
      shiny::tabsetPanel(id = "results", type = "tabs",
       shiny::tabPanel(i_("Answers"),
         icon = icon("align-left"),
         class = "container pt-3 min-vh-50",
         conditionalPanel(
           condition = "input.recompute == 0",
           div(class = "skeleton",
             div(class = "my-3", style = "height:50px;",
               div(class = "row justify-content-center h-50",
                div(class = "card line col-10 col-md-5 h-75")
               ),
               div(class = "row justify-content-center h-50",
                div(class = "card line col-8 col-md-3 h-75")
               )
             ),
             div(class = "row my-3 sqa_panel",
               div(class = "col col-12 col-sm-3 my-1", div(class = "card line h-100")),
               div(class = "col col-12 col-sm-6 my-1", div(class = "card line h-100")),
               div(class = "col col-12 col-sm-3 my-1", div(class = "card line h-100"))
             ),
             div(class = "row my-1", style = "height:50px;",
               div(class = "col", div(class = "card line h-100"))
             ),
             hr(),
             div(class = "bg-white", style = "height:200px;")
           )
         ),
         conditionalPanel(
           condition = "input.recompute == 1",
           conditionalPanel(
             condition = "input.resulted == 0",
             fluidRow(
               class = "justify-content-center min-vh-50 py-5 px-4",
               div(
                 class = "col col-12 justify-content-center text-center pt-5 pb-4 text-light",
                 tags$i(class="display-2 fas fa-microscope")
               ),
               div(
                 class = "col col-12 justify-content-center text-center",
                 h4(i_("No documents matching the specified search terms"))
               ),
               div(
                 class = "col col-12 col-md-6 col-lg-4 justify-content-center",
                 tags$ul(
                   tags$li(i_("Check the spelling of the search terms")),
                   tags$li(i_("Try other keywords"))
                 )
               )
             )
           ),
           conditionalPanel(
             condition = "input.resulted == 1",
             uiOutput("sqa_panel"),
             uiOutput("sqa_filter"), hr(),
             uiOutput("sqa_render"),
             fluidRow(
               class = "text-light justify-content-center p-5",
               paginationUI(
                 "pager", width = 12,
                 offset = 0, class = "text-center")
             )
           )
         )
       ),
       shiny::tabPanel("Corpus",
         icon = icon("chart-area"),
         class = "container pt-3",
         conditionalPanel(
           condition = "input.recompute == 0",
           div(class = "skeleton",
             div(class = "my-3", style = "height:50px;",
               div(class = "row justify-content-center h-50",
                 div(class = "card line col-10 col-md-5 h-75")
               ),
               div(class = "row justify-content-center h-50",
                 div(class = "card line col-8 col-md-3 h-75")
               )
             ),
             fluidRow(
               column(
                 6,
                 class = "order-sm-2 py-5",
                 div(class = "border border-light rounded",
                   div(class = "card-header border-bottom-0 bg-grey",
                     p(
                       class = "text-right m-0 mt-2",
                       strong(i_('Interest over time')),
                       tags$i(class = "far fa-question-circle pl-3 text-muted")
                     )
                   ),
                   div(
                     class = "card-body p-1 bg-grey",
                     div(class = "d-flex align-items-center justify-content-center",
                       style = "height:350px;",
                       tags$i(class = "fas fa-chart-area display-1 text-white-50")
                     )
                   )
                 )
               ),
               column(
                 6,
                 class = "order-sm-1 py-5",
                 div(
                   class = "h-100 overflow-hidden",
                   div(class = "card line h-25 mb-1"),
                   div(class = "card line h-25 my-1"),
                   div(class = "card line h-25 my-1"),
                   div(class = "card line h-25 mt-1")
                 )
               )
             )
           )
         ),
         conditionalPanel(class = "container-fluid justify-content-center",
           condition = "input.recompute == 1",
           conditionalPanel(
             condition = "input.resulted == 0",
             fluidRow(
               class = "justify-content-center min-vh-50 py-5 px-4",
               div(
                 class = "col col-12 justify-content-center text-center pt-5 pb-4 text-light",
                 tags$i(class="display-2 fas fa-capsules")
               ),
               div(
                 class = "col col-12 justify-content-center text-center",
                 h4(i_("No documents matching the specified search terms"))
               ),
               div(
                 class = "col col-12 col-md-6 col-lg-4 justify-content-center",
                 tags$ul(
                   tags$li(i_("Check the spelling of the search terms")),
                   tags$li(i_("Try other keywords"))
                 )
               )
             )
           ),
           conditionalPanel(
             condition = "input.resulted == 1",
             uiOutput("corpus_stat", class = "text-center px-2 py-4"),
             fluidRow(
               column(
                 6,
                 class = "order-sm-2 py-5",
                 cardBox(
                   plotlyOutput("corpus_plot"),
                   status = "gray",
                   header = p(
                     class = "text-right m-0 mt-2",
                     strong(i_("Interest over time"))
                   ),
                   header_class = "border-bottom-0 bg-grey",
                   body_class = "bg-grey"
                 )
                ),
                column(
                  6,
                  class = "order-sm-1 mt-5 mt-md-0 pb-3",
                  DT::dataTableOutput("corpus_art")
               )
             )
           )
         )
       )
      )
    ),
    tags$footer(class = "bg-darkblue py-5 px-5 d-flex justify-content-center",
      fluidRow(class = "container text-light justify-content-center px-0 px-md-3",
        div(
          class = "col row offset-md-3 justify-content-center",
          p(class = "text-light m-0 align-self-center", i_("Created by")),
          tags$img(
            class = "mx-3",
            src = 'https://www.opscidia.com/wp-content/uploads/2019/04/logo_grey.png',
            height ='60', width ='120'
          )
        ),
        div(
          class = "col-md-3",
          selectInput(
            's_lang',
            i_("Change language"),
            choices = i18n$get_languages(),
            selected = i18n$get_key_translation())
        )
      )
    )
  )
))