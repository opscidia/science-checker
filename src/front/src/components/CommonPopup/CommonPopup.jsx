import "./CommonPopup.scss";
import { useCallback, useEffect, useRef } from "react";
import { BsXLg } from "react-icons/bs";
import { PropTypes } from "prop-types";


CommonPopup.propTypes = {
  title: PropTypes.string,
  children: PropTypes.node,
  showPopup: PropTypes.bool,
  closePopup: PropTypes.func,
  type: PropTypes.string,
  className: PropTypes.string,
  showCloseBtn: PropTypes.bool,
};


function CommonPopup({
  title,
  children,
  showPopup,
  closePopup,
  type,
  className = "",
  showCloseBtn = true,
}) {
  const popupRef = useRef();

  const handleClickOutside = useCallback(
    (event) => {
      if (popupRef.current && !popupRef.current.contains(event.target)) {
        closePopup();
      }
    },
    [popupRef, closePopup]
  );

  useEffect(() => {
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showPopup, handleClickOutside]);

  return (
    <div className={className} style={{ zIndex: "1055" }}>
      <div
        className={`common-popup-backdrop fade modal-backdrop ${showPopup ? "show" : ""
          }`}
      ></div>
      <div
        className={`common-popup fade modal ${showPopup ? "show" : ""}`}
        onClick={handleClickOutside}
      >
        <div className="modal-dialog modal-90w modal-md modal-dialog-centered">
          <div className="modal-content" ref={popupRef}>
            <div className={`modal-header ${type === "2" ? "" : "ps-0"}`}>
              {showCloseBtn && (
                <button className="off_canvas_close_btn" onClick={closePopup}>
                  <BsXLg size="0.5em" strokeWidth={1} />
                </button>
              )}
              {title && (
                <div
                  className={`modal-title h6 mx-auto w-75 ${type === "2" ? "text-center" : ""
                    }`}
                >
                  {title}
                </div>
              )}
            </div>
            <div
              className="modal-content-body"
              onClick={(e) => {
                e.stopPropagation();
              }}
            >
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CommonPopup;
