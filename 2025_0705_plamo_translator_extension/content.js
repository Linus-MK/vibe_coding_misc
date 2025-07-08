/**
 * background.jsから送られてくるメッセージを待ち受ける
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // メッセージに翻訳すべきテキストが含まれているか確認
  if (request.text) {
    // ページ内の原文入力用テキストエリアを探す
    // "原文"というラベルを持つ要素の次のtextareaを対象とするなど、より正確なセレクタの指定が望ましい
    const sourceTextArea = document.querySelector('textarea');

    if (sourceTextArea) {
      // テキストエリアに受け取ったテキストを設定
      sourceTextArea.value = request.text;

      // Reactなどのフレームワークにテキストの変更を検知させるため、inputイベントを発火
      const event = new Event('input', { bubbles: true });
      sourceTextArea.dispatchEvent(event);

      // 少し待ってからボタンをクリックすることで、サイト側の処理が追いつくのを待つ
      setTimeout(() => {
        // 「翻訳する」というテキストを持つボタンを探す
        // XPathを使って、テキストが「翻訳する」であるspan要素を持つbuttonを探す
        const xpath = "//button[.//span[text()='翻訳する']]";
        const translateButton = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;

        if (translateButton) {
          translateButton.click();
          sendResponse({ status: "completed" });
        } else {
          console.error("Plamo Quick Translator: Could not find the translate button.");
          sendResponse({ status: "error", message: "Translate button not found" });
        }
      }, 100); // 100ミリ秒待つ

    } else {
      console.error("Plamo Quick Translator: Could not find the source text area.");
      sendResponse({ status: "error", message: "Text area not found" });
    }
  }
  // 非同期のsendResponseを使用する場合はtrueを返す
  return true;
});
