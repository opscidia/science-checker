import { useEffect, useState, useRef, useCallback } from "react";
import { BsXLg } from "react-icons/bs";
import Article from "../../components/Article/Article";
import "./ArticlesPopup.scss";
import { FiRefreshCw, FiSearch } from "react-icons/fi";
import { AiFillInfoCircle } from "react-icons/ai";
import { PropTypes } from "prop-types";
import axios from "axios";
import { getFromLocalStorage, saveToLocalStorage } from "../../utils/utils";
import { IoIosArrowDown, IoIosArrowUp } from "react-icons/io";

ArticlesPopup.propTypes = {
  showArticlesPopup: PropTypes.bool,
  setShowArticlesPopup: PropTypes.func,
  selectedArticles: PropTypes.array,
  setShowCitationsPopup: PropTypes.func,
  setArticleCitation: PropTypes.func,
};

const id = Math.random().toString(36).substring(7);

function ArticlesPopup({
  showArticlesPopup: showPopup,
  setShowArticlesPopup,
  selectedArticles,
  setShowCitationsPopup,
  setArticleCitation
}) {
  const [ws, setWs] = useState(null);
  const myRef = useRef();

  const [question, setQuestion] = useState("");
  const [currentSpanIndex, setCurrentSpanIndex] = useState(-1);
  const [spansCount, setSpansCount] = useState(0);
  const [spansIds, setSpansIds] = useState([]);
  const [connectingSemantic, setConnectingSemantic] = useState(false);
  const [loadingAnswer, setLoadingAnswer] = useState(false);
  const [messageToSend, setMessageToSend] = useState(null);
  const [articles, setArticles] = useState([]);
  const [
    questionsHistory, setQuestionsHistory
  ] = useState(getFromLocalStorage("questionsHistory") || []);

  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const URL_WEB_SOCKET = `${scheme}://${window.location.host}/ws/${id}`;

  const closePopup = useCallback(() => {
    setShowArticlesPopup(false);
    setWs(null);
    setQuestion("");
    setCurrentSpanIndex(-1);
    setSpansCount(0);
    setSpansIds([]);
    setConnectingSemantic(false);
    setLoadingAnswer(false);
    setMessageToSend(null);
    setArticles([]);
  }, [setShowArticlesPopup]);

  const handleClickOutside = useCallback(
    (e) => {
      if (myRef.current.contains(e.target)) {
        closePopup();
      }
    },
    [myRef, closePopup]
  );

  useEffect(() => {
    if (showPopup) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [handleClickOutside, showPopup]);

  useEffect(() => {
    const fetchArticles = async () => {
      try {
        const promises = selectedArticles.map(id => axios.get(`/api/article/${id}`));
        const articlesResponses = await Promise.all(promises);
        const newArticles = articlesResponses.map(response => response.data);
        setArticles(newArticles);
        return newArticles;
      } catch (error) {
        console.error(error);
      }
    }
    if (showPopup && selectedArticles.length > 0) {
      fetchArticles().then((newArticles) => {
        const wsClient = new WebSocket(URL_WEB_SOCKET);
        wsClient.onopen = () => {
          setWs(wsClient);
          wsClient.send(
            JSON.stringify({
              type: "select_articles",
              articles: newArticles.map(article => ({
                ...article,
                id: article?._id,
                content: article?.abstract,
              }))
            })
          );
          setConnectingSemantic(false);
        };
        setQuestionsHistory(getFromLocalStorage("questionsHistory") || []);
        return () => {
          wsClient.close();
        };
      });
    } else setWs();
  }, [showPopup, selectedArticles, URL_WEB_SOCKET]);

  useEffect(() => {
    if (ws) {
      ws.onmessage = (event) => {
        const { data, type } = JSON.parse(event.data);

        if (type === "question.answered") {
          setLoadingAnswer(false);
          let newSpansCount = 0;
          let newSpansIds = [];
          // Make sure articles are ordered by score
          const articlesOrderedByScore = data.sort((a, b) => b.score - a.score);

          for (let i = 0; i < articlesOrderedByScore.length; i++) {
            const answers = articlesOrderedByScore[i].answer;
            if (answers.length > 0) {
              const spanRegex = /<span[^>]*class="hglt__answer"[^>]*>/g;
              const spanMatches = articlesOrderedByScore[i].content.match(spanRegex);
              if (spanMatches) {
                newSpansCount += spanMatches.length;

                spanMatches.forEach((span, index) => {
                  const id = `span-${i}-${index}`;
                  newSpansIds.push(id);
                  articlesOrderedByScore[i].content = articlesOrderedByScore[i].content.replace(span, `${span.slice(0, -1)} id="${id}">`);
                });
              }
            }
          }
          // order articlesOrderedByScore by the original articles order
          const newArticles = selectedArticles.map((id) => articlesOrderedByScore.find((article) => article._id === id));
          setSpansCount(newSpansCount);
          setSpansIds(newSpansIds);
          setArticles(newArticles);

          // Update the questions history in local storage
          let answers_count = 0;
          for (let i = 0; i < data.length; i++) {
            answers_count += data[i].answer ? data[i].answer.length : 1;
          }
          let newQuestion = {
            id: questionsHistory.length + 1,
            question,
            answers_count,
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
  }, [articles, ws, question, questionsHistory, selectedArticles]);

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
                  <div className="modal-content-body-article d-flex flex-column"
                  >
                    {(articles?.[0]?.answer?.length > 0) && <div className="article_content__answers text-center p-4">
                      <div
                        className="d-flex align-items-center w-fit-content mx-auto"
                      >
                        <div
                          className="article_content__answers__count"
                        >
                          {spansIds.length} answers for this question:
                        </div>
                        <div className="article_content__answers__question ms-2">
                          {question}
                        </div>
                      </div>
                      <div className="article_content__answers__answer mt-2">
                        Answer {currentSpanIndex + 1} of {spansCount}
                        <IoIosArrowUp
                          className="c-pointer ms-2"
                          size="1.2em"
                          onClick={() => {
                            if (currentSpanIndex <= 0) return;
                            setCurrentSpanIndex(currentSpanIndex - 1);
                            scrollToSpan(spansIds[currentSpanIndex - 1]);
                          }}
                        />
                        <IoIosArrowDown
                          className="c-pointer ms-1"
                          size="1.2em"
                          onClick={() => {
                            if (currentSpanIndex === spansCount - 1) return;
                            setCurrentSpanIndex(currentSpanIndex + 1);
                            scrollToSpan(spansIds[currentSpanIndex + 1]);
                          }}
                        />
                      </div>
                    </div>}
                    <div className="articles_list p-4"
                      id="articles_list"
                    >
                      {articles.map((article) => (
                        <Article
                          key={article.id}
                          {...article}
                          {...{ setArticleCitation, setShowCitationsPopup }}
                        />
                      ))}
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
  const div = document.getElementById("articles_list");
  const span = document.getElementById(currentSpanId);
  if (span) {
    let position = span.offsetTop;
    let currentParent = span.offsetParent;
    while (currentParent && currentParent !== div) {
      position += currentParent.offsetTop;
      currentParent = currentParent.offsetParent;
    }
    div.scrollTo({ behavior: "smooth", top: position - div.offsetTop });
  }
}

export default ArticlesPopup;
