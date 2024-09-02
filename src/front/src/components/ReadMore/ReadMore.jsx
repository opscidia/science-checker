import "./ReadMore.scss";
import { useState } from "react";
import Latex from "react-latex";
import { Marker } from "react-mark.js";
import { PropTypes } from "prop-types";

const textLimit = 400;

const ReadMore = ({ children, highlights = [] }) => {
  const text = children;
  const textToRender = children;

  const [isReadMore, setIsReadMore] = useState(true);
  const toggleReadMore = (event) => {
    event.stopPropagation();
    setIsReadMore(!isReadMore);
  };

  return (
    <div className="readmore text mb-2">
      <>
        <Marker
          mark={
            !highlights || !Array.isArray(highlights)
              ? ""
              : highlights?.join(" ") || ""
          }
        >
          <>
            <Latex>{isReadMore ? text?.slice(0, textLimit) : text}</Latex>
          </>
        </Marker>

        {text && textToRender?.length > textLimit && (
          <span onClick={toggleReadMore} className="read-or-hide">
            {isReadMore ? " expand ..." : " show less"}
          </span>
        )}
      </>
    </div>
  );
};

ReadMore.propTypes = {
  children: PropTypes.string,
  highlights: PropTypes.array,
};

export default ReadMore;
