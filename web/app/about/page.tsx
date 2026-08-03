import FrontPage from "../page";

/** /about re-exports the front page so every link shipped before the landing
 *  moved to the root keeps working. One page, two addresses. */
export { metadata } from "../page";
export default FrontPage;
