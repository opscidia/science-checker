import "./Article.scss";
import { useState } from "react";
import { IoIosPaper } from "react-icons/io";
import Latex from "react-latex";
import { Marker } from "react-mark.js";
import { FaQuoteRight } from "react-icons/fa";
import { BsShareFill } from "react-icons/bs";
import { Form } from "react-bootstrap";
import ReadMore from "../ReadMore/ReadMore";
import {
  completeHTML,
  filterTextKeywordsByTag,
  filterTextTitleByTag,
  renderCitations,
} from "../../utils/utils";
import { PropTypes } from "prop-types";

Article.propTypes = {
  id: PropTypes.string,
  custom_publication_date: PropTypes.string,
  container: PropTypes.string,
  title: PropTypes.string,
  DOI: PropTypes.string,
  content: PropTypes.string,
  citation: PropTypes.number,
  highlights: PropTypes.object,
  authors: PropTypes.array,
  bibtex: PropTypes.string,
  apa: PropTypes.string,
  mla: PropTypes.string,
  iso690: PropTypes.string,
  onClick: PropTypes.func,
  selectedArticles: PropTypes.array,
  handleChange: PropTypes.func,
  type: PropTypes.string,
  score: PropTypes.number,
  setShowCitationsPopup: PropTypes.func,
  setArticleCitation: PropTypes.func,
};

function Article({
  id,
  custom_publication_date: date,
  container: title_container,
  title,
  DOI: doi,
  content,
  citation,
  highlights: articleHighlights,
  authors,
  bibtex: bibCitation,
  apa: apaCitation,
  mla: mlaCitation,
  iso690: isoCiation,
  onClick,
  selectedArticles,
  handleChange,
  type,
  score,
  setShowCitationsPopup,
  setArticleCitation,
}) {
  const highlightsTitle = filterTextTitleByTag(articleHighlights?.title || "");
  const highlights = filterTextKeywordsByTag(articleHighlights?.abstract || []);

  const renderArticleIcon = () => {
    return <IoIosPaper className="me-2" />;
  };

  const onClickCitations = (event) => {
    event.stopPropagation();

    setShowCitationsPopup(true);
    setArticleCitation({
      bibCitation,
      apaCitation,
      mlaCitation,
      isoCiation
    });
  };

  return (
    <div className={`content d-flex ${type !== "search" ? "w-100 bg__dark" : "search_animate"}`}>
      {
        type === "search" &&
        <div className="content__checkbox">
          <Form.Check
            inline
            name="group1"
            type={"checkbox"}
            checked={selectedArticles.includes(id)}
            onChange={handleChange(id)}
          />
        </div>}
      <div className="content__wrapper c-pointer" onClick={onClick || null}>
        {score && <span
          className="content__score__badge"
        >
          Score: {score.toFixed(2)}%
        </span>}
        <div className="content__header d-flex mb-2">
          <span className="d-flex align-items-center">
            {renderArticleIcon()}
            <Marker mark={highlightsTitle?.join(" ") || ""}>
              <Latex>{title}</Latex>
            </Marker>
          </span>
        </div>
        <div className="content__title d-flex flex-wrap align-items-center mb-1">
          {date}
          {authors.length > 0 && <span className="dot"></span>}
          {authors.length > 0 && authors[0] && <RenderAuthors {...{ authors }} />}
          {title_container && <span className="dot"></span>}
          {title_container}
        </div>
        <div className="content__doi mb-2">{doi}</div>
        <div className="content__description d-flex">
          {type === "search" ? <ReadMore highlights={highlights}>{content}</ReadMore> :

            <span
              dangerouslySetInnerHTML={{
                __html: content
                  ? completeHTML(content)
                  : "",
              }}
            ></span>}
        </div>
        <div className="content__footer d-inline">
          <div className="d-inline-block">
            <>
              <div
                className="content__footer__cite d-inline"
                onClick={onClickCitations}
              >
                <FaQuoteRight size="1em" /> Cite
              </div>
              <div className="content__footer__citation d-inline">
                <BsShareFill className="ms-3 me-1" size="1em" />{" "}
                {renderCitations(citation)}
              </div>
            </>
          </div>
        </div>
      </div>
    </div >
  );
}
export default Article;

export const RenderAuthors = ({ authors }) => {
  const [showMoreAuthors, setShowMoreAuthors] = useState(false);
  const limit = 16;

  const checkConcatenate = (author) => {
    let regexp = /[A-Za-z]+,\s[A-Za-z]\./gi;
    return author.match(regexp) && author.match(regexp).length > 0;
  };
  const authorsList = !showMoreAuthors ? authors.slice(0, limit) : authors;
  const newAuthorsList = authorsList.map((author) => (
    <span key={author} role="button">
      {checkConcatenate(author) == null || checkConcatenate(author) === false
        ? author[0].concat(" ", author.split(" ").slice(-1))
        : author}
    </span>
  ));

  return authors.length > 0 && newAuthorsList.length > 0 ? (
    <>
      <div className="d-flex flex-wrap">
        {newAuthorsList.map((author, index) => {
          return (
            <div className="d-flex" key={index}>
              <span key={index}>
                {author}
                {index < newAuthorsList.length - 1 && ", "}
              </span>
            </div>
          );
        })}
      </div>

      {!showMoreAuthors && authors.length > limit ? (
        <span
          className="authors_list ms-1"
          onClick={() => {
            setShowMoreAuthors(true);
          }}
        >
          more ...
        </span>
      ) : showMoreAuthors && authors.length > limit ? (
        <span
          className="authors_list ms-1"
          onClick={() => {
            setShowMoreAuthors(false);
          }}
        >
          less
        </span>
      ) : (
        ""
      )}
    </>
  ) : null;
};

RenderAuthors.propTypes = {
  authors: PropTypes.array,
};
