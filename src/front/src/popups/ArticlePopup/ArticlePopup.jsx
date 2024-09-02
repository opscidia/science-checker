import { useEffect, useState, useRef, useCallback } from "react";
import { BsXLg } from "react-icons/bs";
import { RenderAuthors } from "../../components/Article/Article";
import "./ArticlePopup.scss";
import { IoIosArrowDown, IoIosArrowUp } from "react-icons/io";
import Latex from "react-latex";
import { Marker } from "react-mark.js";
// import { toast } from "react-toastify";
import { FiRefreshCw, FiSearch } from "react-icons/fi";
import { AiFillInfoCircle } from "react-icons/ai";
import ReadMore from "../../components/ReadMore/ReadMore";
import { PropTypes } from "prop-types";
import { completeHTML, getFromLocalStorage, saveToLocalStorage } from "../../utils/utils";

ArticlePopup.propTypes = {
  showArticlePopup: PropTypes.bool,
  setShowArticlePopup: PropTypes.func,
  articleData: PropTypes.object,
};

const id = Math.random().toString(36).substring(7);

function ArticlePopup({
  showArticlePopup: showPopup,
  setShowArticlePopup,
  articleData,
}) {
  const [ws, setWs] = useState(null);
  const myRef = useRef();
  const [article, setArticle] = useState(articleData);
  const [question, setQuestion] = useState("");
  const [currentSpanIndex, setCurrentSpanIndex] = useState(-1);
  const [spansCount, setSpansCount] = useState(0);
  const [spansIds, setSpansIds] = useState([]);
  const [connectingSemantic, setConnectingSemantic] = useState(false);
  const [loadingAnswer, setLoadingAnswer] = useState(false);
  const [messageToSend, setMessageToSend] = useState(null);
  const [
    questionsHistory, setQuestionsHistory
  ] = useState(getFromLocalStorage("questionsHistory") || []);

  const {
    custom_publication_date,
    container_title,
    title,
    highlightsTitle,
    DOI: doi,
    abstract,
    URLs: urls,
    authors,
  } = articleData;
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const URL_WEB_SOCKET = `${scheme}://${window.location.host}/ws/${id}`;

  const closePopup = useCallback(() => {
    setArticle({});
    setShowArticlePopup(false);
    setWs(null);
    setQuestion("");
    setCurrentSpanIndex(-1);
    setSpansCount(0);
    setSpansIds([]);
    setConnectingSemantic(false);
    setLoadingAnswer(false);
    setMessageToSend(null);
  }, [setShowArticlePopup]);

  const handleClickOutside = useCallback(
    (e) => {
      if (myRef.current.contains(e.target)) {
        closePopup();
      }
    },
    [myRef, closePopup]
  );

  useEffect(() => {
    setArticle(articleData);
  }, [articleData]);

  useEffect(() => {
    if (showPopup) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [handleClickOutside, showPopup]);

  useEffect(() => {
    if (showPopup) {
      const wsClient = new WebSocket(URL_WEB_SOCKET);
      wsClient.onopen = () => {
        setWs(wsClient);
        wsClient.send(
          JSON.stringify({
            type: "select_articles",
            articles: [
              {
                ...articleData,
                id: articleData?._id,
                content: articleData?.abstract,
              },
            ],
          })
        );
        setConnectingSemantic(false);
      };
      setQuestionsHistory(getFromLocalStorage("questionsHistory") || []);
      return () => {
        wsClient.close();
      };
    } else setWs();
  }, [URL_WEB_SOCKET, showPopup, articleData]);

  useEffect(() => {
    if (ws) {
      ws.onmessage = (event) => {
        const { data, type } = JSON.parse(event.data);
        const answers = data?.[0]?.answer;
        const sections = [{
          content: data[0].content,
        }]
        const newSections = sections;
        let newSpansCount = 0;
        let newSpansIds = [];

        if (type === "question.answered") {
          setLoadingAnswer(false);
          setArticle(data[0]);
          // if (answers.length > 0)
          //   answers.forEach((section_with_answers_id) => {
          //     const spanRegex = /<span[^>]*class="hglt__answer"[^>]*>/g;
          //     const spanMatches =
          //       sections[section_with_answers_id].content.match(spanRegex);
          //     if (spanMatches) {
          //       newSpansCount += spanMatches.length;

          //       spanMatches.forEach((span, index) => {
          //         const id = `span-${section_with_answers_id}-${index}`;
          //         newSpansIds.push(id);
          //         newSections[section_with_answers_id].content = sections[
          //           section_with_answers_id
          //         ].content.replace(span, `${span.slice(0, -1)} id="${id}">`);
          //       });
          //     }
          //   });

          setSpansCount(newSpansCount);
          setSpansIds(newSpansIds);
          setArticle((article) => ({
            ...article,
            sections: newSections,
          }));

          // Update the questions history in local storage
          let newQuestion = {
            id: questionsHistory.length + 1,
            question,
            answers_count: answers ? answers.length : 1,
            date: new Date(),
          };
          // Check if the question is already in the history
          const questionIndex = questionsHistory.findIndex(
            (q) => q.question === question
          );
          const newQuestionsHistory = questionsHistory;
          if (questionIndex !== -1) {
            newQuestionsHistory[questionIndex].answers_count =
              newQuestion.answers_count;
            newQuestionsHistory[questionIndex].date = newQuestion.date;
          } else {
            newQuestionsHistory.push(newQuestion);
          }
          setQuestionsHistory(newQuestionsHistory);
          saveToLocalStorage("questionsHistory", newQuestionsHistory);
        }
      };
    }
  }, [setArticle, ws, question, questionsHistory]);

  useEffect(() => {
    if (ws?.readyState === WebSocket.OPEN && messageToSend) {
      ws.send(messageToSend);
      setMessageToSend(null);
    }
  }, [messageToSend, ws]);

  useEffect(() => {
    if (currentSpanIndex !== -1) {
      const span = document.getElementById(spansIds[currentSpanIndex]);
      if (span) {
        span.classList.add("hglt__selected");
      }
      // delete hglt__selected class from all other spans
      for (let i = 0; i < spansIds.length; i++) {
        if (i !== currentSpanIndex) {
          const span = document.getElementById(spansIds[i]);
          if (span) {
            span.classList.remove("hglt__selected");
          }
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSpanIndex]);

  const askQuestion = () => {
    if (loadingAnswer) return;
    setLoadingAnswer(true);

    const message = JSON.stringify({
      type: "discuss",
      query: question,
    });

    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(message);
    } else {
      setMessageToSend(message);
    }
  };

  return (
    <>
      <div
        className={`article-popup-backdrop fade modal-backdrop ${showPopup ? "show" : ""
          }`}
        ref={myRef}
      ></div>
      <div className={`article-popup fade modal ${showPopup ? "show" : ""}`}>
        <div className="modal-dialog modal-90w modal-md modal-dialog-centered">
          {showPopup && (
            <div className="modal-content" onClick={handleClickOutside}>
              <div className={`modal-header pe-2`}>
                <button className="popup_close_btn" onClick={closePopup}>
                  <BsXLg strokeWidth={3} />
                </button>
                <div className="ms-auto d-flex align-items-center">
                  {connectingSemantic && (
                    <div className="d-flex align-items-center">
                      <FiRefreshCw
                        className={"spinning me-2"}
                        color="#5C7FD3"
                      />
                      <span className="spinning-text me-3">Connecting ...</span>
                    </div>
                  )}
                  {loadingAnswer && (
                    <div className="d-flex align-items-center">
                      <FiRefreshCw
                        className={"spinning me-2"}
                        color="#5C7FD3"
                      />
                      <span className="spinning-text me-3">
                        Loading answer ...
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <div className="modal-content-body d-flex p-4">
                <div className="modal-content-body__input__container me-4">
                  <div className="modal-content-body__searchbar mb-4">
                    <div className="position-relative m-3 ms-4 w-100">
                      <input
                        className="search-input px-5"
                        type="text"
                        placeholder="Ask your question"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            e.stopPropagation();
                            askQuestion();
                          }
                        }}
                        disabled={loadingAnswer}
                      />
                      <AiFillInfoCircle
                        color="#AEC0D3"
                        size="1em"
                        className="position-absolute"
                        style={{ right: "10px", top: "10px" }}
                      />
                      <FiSearch
                        className="search__icon__btn position-absolute top-50 start-0 translate-middle-y ms-3 me-2"
                        color="#000"
                        size="1em"
                        onClick={askQuestion}
                      />
                    </div>
                  </div>
                  <div className="modal-content-body__questions__history d-flex flex-column">
                    <div className="modal-content-body__questions__history__title ms-1 mt-1 mb-3">
                      Previous Question
                    </div>
                    <div className="modal-content-body__questions__history__list ms-1">
                      {questionsHistory.map((q) => (
                        <div
                          key={q.id}
                          className="modal-content-body__questions__history__item mb-1 d-flex align-items-center"
                        >
                          <div className="modal-content-body__questions__history__item__question c-pointer"
                            onClick={() => {
                              setQuestion(q.question);
                            }}
                          >
                            {q.question}
                          </div>
                          <span className="dot"></span>
                          <div className="modal-content-body__questions__history__item__answers">
                            {q.answers_count} answers
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                <div
                  className="me-3 h-100 d-flex flex-column"
                  id={"article_container"}
                  style={{
                    width: "58%",
                  }}
                >
                  <div className="modal-content-body-article d-flex flex-column">
                    {(article?.answer?.length > 0 ||
                      article?.answer === 0) && (
                        <div className="article_content__answers text-center p-4">
                          <div className="d-flex align-items-center w-fit-content mx-auto">
                            <div className="article_content__answers__count">
                              {article?.answer === 0
                                ? "1 answer"
                                : `${article?.answer.length} answers`}{" "}
                              for this question:
                            </div>
                            <div className="article_content__answers__question ms-2">
                              {question}
                            </div>
                          </div>
                          <div className="article_content__answers__answer mt-2">
                            {article?.answer > 1
                              ? `Answer ${currentSpanIndex + 1} of ${spansCount}`
                              : "Answer 1 of 1"}

                            <span className="article_content__btns c-pointer ms-3">
                              <IoIosArrowUp
                                size="1em"
                                onClick={() => {
                                  if (currentSpanIndex <= 0) return;
                                  setCurrentSpanIndex(currentSpanIndex - 1);
                                  scrollToSpan(spansIds[currentSpanIndex - 1]);
                                }}
                              />
                            </span>

                            <span className="article_content__btns c-pointer ms-2">
                              <IoIosArrowDown
                                size="1em"
                                onClick={() => {
                                  if (currentSpanIndex === spansCount - 1) return;
                                  setCurrentSpanIndex(currentSpanIndex + 1);
                                  scrollToSpan(spansIds[currentSpanIndex + 1]);
                                }}
                              />
                            </span>
                          </div>
                        </div>
                      )}
                    <div className="p-4">
                      <div className="article_content">
                        <div className="article_content__header d-flex mb-2">
                          <span
                            className={
                              "article_title_c d-flex align-items-center article_title_hover"
                            }
                            onClick={() => {
                              window.open(urls[0], "_blank");
                            }}
                          >
                            <Marker mark={highlightsTitle?.join(" ") || ""}>
                              <Latex>{title}</Latex>
                            </Marker>
                          </span>
                        </div>
                        <span className="article_content__title d-flex align-items-center flex-wrap mb-2">
                          {custom_publication_date}
                          {authors.length > 0 && <span className="dot"></span>}
                          {authors.length > 0 && authors[0] && (
                            <RenderAuthors {...{ authors }} />
                          )}
                          {container_title && <span className="dot"></span>}
                          {container_title}
                        </span>

                        <div className="content__doi mb-2">{doi}</div>
                        <div className="article_content__description d-flex flex-column mb-1">
                          <ReadMore>{abstract}</ReadMore>
                        </div>
                        {/* <div className="content__footer d-inline">
                        <div className="d-inline-block">
                          <>
                            <div
                              className="content__footer__cite d-inline"
                              //   onClick={onClickCitations}
                            >
                              <FaQuoteRight size="1em" /> Cite
                            </div>
                            <div className="content__footer__citation d-inline">
                              <BsShareFill className="ms-3 me-1" size="1em" />{" "}
                              {renderCitations(citation)}
                            </div>
                          </>
                        </div>
                      </div> */}
                      </div>
                      <div className="d-flex align-items-center flex-wrap pb-3 mt-1">
                        {/* <Form.Check
                        className="c-pointer  mt-2"
                        type="switch"
                        id="custom-switch"
                        label=" Translate the abstract into french"
                        checked={translate}
                        onChange={handleTranslateSwitch}
                      /> */}
                      </div>
                      <>
                        <div
                          className="article_content__footer__sections__title p-2 mt-2 ps-4"
                          style={{
                            color: "#ffffff",
                            backgroundColor: "#AEC0D3",
                          }}
                        >
                          Full text
                        </div>
                        <div className="article_content__footer__sections d-flex flex-column p-2 mt-1 flex-grow-1 overflow-auto">
                          <div
                            className="article__fulltext"
                            id="article_fulltext"
                          >
                            {article?.sections?.map((section) => (
                              <div
                                className="d-flex flex-column py-3 pe-2"
                                key={section._id}
                              >
                                <h5>{section.title}</h5>
                                <span
                                  className="search__section"
                                  key={section._id}
                                  dangerouslySetInnerHTML={{
                                    __html: section.content
                                      ? completeHTML(section.content)
                                      : "",
                                  }}
                                ></span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function scrollToSpan(currentSpanId) {
  const div = document.getElementById("article_fulltext");
  const span = document.getElementById(currentSpanId);
  if (span) {
    div.scrollTo({ behavior: "smooth", top: span.offsetTop - div.offsetTop });
  }
}

export default ArticlePopup;
