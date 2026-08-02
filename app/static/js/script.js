
const toggleDropdown = (dropdown, menu, isOpen) => {
  dropdown.classList.toggle("open", isOpen);
  menu.style.height = isOpen ? `${menu.scrollHeight}px` : 0;
};

// Close all open dropdowns
const closeAllDropdowns = () => {
  document.querySelectorAll(".dropdown-container.open").forEach((openDropdown) => {
    toggleDropdown(openDropdown, openDropdown.querySelector(".dropdown-menu"), false);
  });
};

// Attach click event to all dropdown toggles
document.querySelectorAll(".dropdown-toggle").forEach((dropdownToggle) => {
  dropdownToggle.addEventListener("click", (e) => {
    e.preventDefault();

    const dropdown = dropdownToggle.closest(".dropdown-container");
    const menu = dropdown.querySelector(".dropdown-menu");
    const isOpen = dropdown.classList.contains("open");

    closeAllDropdowns(); // Close all open dropdowns
    toggleDropdown(dropdown, menu, !isOpen); // Toggle current dropdown visibility
  });
});

// Attach click event to sidebar toggle buttons
document.querySelectorAll(".sidebar-toggler, .sidebar-menu-button").forEach((button) => {
  button.addEventListener("click", () => {
    closeAllDropdowns(); // Close all open dropdowns
    document.querySelector(".sidebar").classList.toggle("collapsed"); // Toggle collapsed class on sidebar
  });
});

//chặn submit form khi nhấn Enter trong input
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT') {
        const form = e.target.closest('form[method="POST"]');
        if (!form) return;

        e.preventDefault(); // Chặn submit và đứng trang

        // 1. Lấy tất cả input không phải hidden
        const allInputs = Array.from(form.querySelectorAll('input:not([type="hidden"])'));
        const currentIndex = allInputs.indexOf(e.target);

        // 2. Nếu đang ở ô cuối cùng (box_note[]) -> Thực hiện thêm dòng
        if (e.target.name === "box_note[]") {
            const addBtn = form.querySelector('.add-row, [id*="add"], [onclick*="addRow"]');
            if (addBtn) {
                addBtn.click();
                setTimeout(() => {
                    const freshInputs = Array.from(form.querySelectorAll('input:not([type="hidden"])'));
                    // Tìm ô đầu tiên của dòng mới (ô nằm sau ô note vừa rồi)
                    const nextAfterNote = freshInputs[freshInputs.indexOf(e.target) + 1];
                    if (nextAfterNote) {
                        nextAfterNote.focus();
                    }
                }, 100);
            }
            return;
        }

        // 3. Nếu đang ở ô giữa (ví dụ: Số lượng, Đơn giá...) -> Nhảy qua ô Readonly
        let nextInput = null;
        for (let i = currentIndex + 1; i < allInputs.length; i++) {
            // Điều kiện: Không bị readonly, không bị disabled
            if (!allInputs[i].readOnly && !allInputs[i].disabled) {
                nextInput = allInputs[i];
                break;
            }
            // Hoặc nếu là ô Note (cột cuối) thì vẫn nhảy vào dù nó là gì
            if (allInputs[i].name === "box_note[]") {
                nextInput = allInputs[i];
                break;
            }
        }

        // 4. Thực hiện nhảy focus
        if (nextInput) {
            nextInput.focus();
            if (typeof nextInput.select === "function") {
                nextInput.select(); // Bôi đen nội dung để nhập đè nhanh
            }
        }
    }
});

// Collapse sidebar by default on small screens
if (window.innerWidth <= 1024) document.querySelector(".sidebar").classList.add("collapsed");
