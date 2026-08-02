/* giúp auto-gợi ý code ngay trên UI khi người dùng nhập tên sản phẩm*/

const ProductCode = (() => {
  "use strict";

  async function slugFromName(name = "") {
    const s = (name || "").trim();
    if (!s) return "";
    try {
      const res = await fetch(
        `/api/products/slug-code?name=${encodeURIComponent(s)}`,
      );
      const data = await res.json();
      return data && data.ok && data.code
        ? String(data.code).toUpperCase()
        : "";
    } catch (_) {
      return "";
    }
  }

  return {
    slugFromName,
    quickSlugProductCode: slugFromName,
  };
})();
