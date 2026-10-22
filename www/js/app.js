// Logic điều khiển chính cho Ứng dụng Trợ Lý Tư Vấn Học Sinh THCS (Tuổi 13, 14, 15)

(function () {
  const STATE_KEY = "thcs_student_profile_v1";
  const CHAT_KEY = "thcs_chat_history_v1";
  const MOOD_KEY = "thcs_mood_logs_v1";
  const QUIZ_HISTORY_KEY = "thcs_quiz_results_v1";

  let profile = {
    name: "Bạn nhỏ",
    age: 14, // 13, 14, or 15
    persona: "may", // "may" or "expert"
    theme: "light",
    parentPhone: "",
    teacherPhone: "",
    diaryPin: ""
  };

  let chatHistory = [];
  let moodLogs = [];
  let quizHistory = [];
  let selectedMoodScore = 5;
  let selectedMoodEmoji = "😊";
  let selectedMoodLabel = "Vui vẻ";
  let diaryUnlocked = false;

  // Breathing & Audio state
  let breathInterval = null;
  let breathTimeouts = [];
  let isBreathing = false;
  let audioCtx = null;
  let ambientNode = null;
  let isAmbientPlaying = false;

  // Pomodoro state
  let pomoSeconds = 25 * 60;
  let pomoTimer = null;
  let pomoRunning = false;

  // Active Quiz state
  let activeQuiz = null;
  let activeQuizIndex = 0;
  let activeQuizAnswers = [];

  // PWA Install Prompt
  let deferredInstallPrompt = null;

  function loadState() {
    try {
      const savedProfile = localStorage.getItem(STATE_KEY);
      if (savedProfile) {
        profile = { ...profile, ...JSON.parse(savedProfile) };
      }
      const savedChat = localStorage.getItem(CHAT_KEY);
      if (savedChat) {
        chatHistory = JSON.parse(savedChat);
      }
      const savedMoods = localStorage.getItem(MOOD_KEY);
      if (savedMoods) {
        moodLogs = JSON.parse(savedMoods);
      }
      const savedQuizzes = localStorage.getItem(QUIZ_HISTORY_KEY);
      if (savedQuizzes) {
        quizHistory = JSON.parse(savedQuizzes);
      }
    } catch (e) {
      console.error("Error loading state:", e);
    }
  }

  function saveProfile() {
    localStorage.setItem(STATE_KEY, JSON.stringify(profile));
  }

  function saveChat() {
    localStorage.setItem(CHAT_KEY, JSON.stringify(chatHistory.slice(-40)));
  }

  function saveMoods() {
    localStorage.setItem(MOOD_KEY, JSON.stringify(moodLogs.slice(0, 60)));
  }

  function showToast(msg) {
    const toast = document.getElementById("toast-msg");
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 2600);
  }

  function applyTheme() {
    document.documentElement.setAttribute("data-theme", profile.theme || "light");
    const themeBtn = document.getElementById("btn-theme-toggle");
    if (themeBtn) {
      themeBtn.textContent = profile.theme === "dark" ? "☀️" : "🌙";
    }
  }

  // Navigation
  window.switchTab = function (tabId) {
    document.querySelectorAll(".tab-panel").forEach((el) => {
      el.classList.toggle("active", el.id === `tab-${tabId}`);
    });
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabId);
    });
    window.scrollTo({ top: 0, behavior: "smooth" });

    if (tabId === "chat") {
      scrollToBottomChat();
    } else if (tabId === "mood") {
      renderMoodSection();
    } else if (tabId === "quiz") {
      renderQuizList();
    } else if (tabId === "handbook") {
      renderHandbook();
    }
  };

  window.switchMoodSubTab = function (subId) {
    document.querySelectorAll(".mood-subpanel").forEach((el) => {
      el.style.display = el.id === `mood-sub-${subId}` ? "block" : "none";
    });
    document.querySelectorAll("#tab-mood .sub-tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.sub === subId);
    });
  };

  // Age Profile Selection (13, 14, 15)
  window.selectAge = function (age) {
    profile.age = Number(age);
    saveProfile();
    renderHomeAgeContent();
    renderChatQuickPrompts();
    renderHandbook();
    showToast(`Đã chuyển sang chế độ tư vấn Tuổi ${age} (${window.THCS_DATA.ageProfiles[age].grade})`);
  };

  function renderHomeAgeContent() {
    const ageInfo = window.THCS_DATA.ageProfiles[profile.age] || window.THCS_DATA.ageProfiles[14];

    // Header & Hero
    document.getElementById("header-subtitle").innerHTML =
      `<span class="status-dot"></span> Đồng hành ${ageInfo.grade} (${ageInfo.age} tuổi)`;
    document.getElementById("hero-name").textContent = profile.name || "Bạn nhỏ";
    document.getElementById("hero-grade-badge").textContent = `${ageInfo.age} Tuổi • ${ageInfo.grade}`;

    // Age pills
    document.querySelectorAll(".age-pill").forEach((btn) => {
      btn.classList.toggle("active", Number(btn.dataset.age) === Number(profile.age));
    });

    // Age focus card
    document.getElementById("age-focus-title").textContent = ageInfo.title;
    document.getElementById("age-focus-summary").textContent = ageInfo.summary;

    const tagsContainer = document.getElementById("age-focus-tags");
    tagsContainer.innerHTML = ageInfo.focusTags
      .map(
        (tag) =>
          `<button class="topic-chip" onclick="askFromHome('${tag.query.replace(/'/g, "\\'")}')">
            <span>${tag.icon}</span> ${tag.text}
          </button>`
      )
      .join("");
  }

  window.refreshDailyQuote = function () {
    const quotes = window.THCS_DATA.dailyQuotes;
    const randomQuote = quotes[Math.floor(Math.random() * quotes.length)];
    document.getElementById("daily-quote-text").textContent = randomQuote;
  };

  window.askFromHome = function (queryText) {
    window.switchTab("chat");
    const input = document.getElementById("chat-input");
    input.value = queryText;
    window.sendChatMessage();
  };

  // Quick Mood Check-in on Home
  window.quickMoodCheckIn = function (score, emoji, label) {
    selectedMoodScore = score;
    selectedMoodEmoji = emoji;
    selectedMoodLabel = label;

    document.querySelectorAll(".mood-btn").forEach((b) => {
      b.classList.toggle("selected", Number(b.dataset.score) === score);
    });

    const feedbackEl = document.getElementById("home-mood-feedback");
    feedbackEl.style.display = "block";
    if (score >= 4) {
      feedbackEl.innerHTML = `${emoji} Tuyệt quá! Cảm xúc hôm nay của cậu là <strong>${label}</strong>. Bấm <a href="javascript:void(0)" onclick="switchTab('mood')" style="color:var(--primary);font-weight:700;">Lưu vào Nhật ký</a> hoặc kể niềm vui cho <strong>banem</strong> nghe nhé!`;
    } else if (score === 3) {
      feedbackEl.innerHTML = `${emoji} Một ngày <strong>${label}</strong>. Nếu muốn thư giãn đầu óc, hãy ghé góc <a href="javascript:void(0)" onclick="switchTab('mood');switchMoodSubTab('relax')" style="color:var(--primary);font-weight:700;">Hít thở 4-7-8</a> nhé!`;
    } else {
      feedbackEl.innerHTML = `${emoji} Cậu đang cảm thấy <strong>${label}</strong> ư? Đừng giữ trong lòng một mình nhé, hãy <a href="javascript:void(0)" onclick="askFromHome('Hôm nay mình cảm thấy ${label.toLowerCase()} và mệt mỏi quá')" style="color:var(--primary);font-weight:700;">Tâm sự ngay với banem</a> nha!`;
    }
  };

  // CHAT MODULE
  window.selectPersona = function (persona) {
    profile.persona = persona;
    saveProfile();
    document.querySelectorAll(".persona-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.persona === persona);
    });
    const label = persona === "expert" ? "Chuyên gia Tâm lý Học đường" : "Chatbot banem";
    showToast(`Đã chọn người tư vấn: ${label}`);
  };

  function renderChatQuickPrompts() {
    const ageInfo = window.THCS_DATA.ageProfiles[profile.age] || window.THCS_DATA.ageProfiles[14];
    const container = document.getElementById("chat-quick-prompts");
    if (!container) return;
    container.innerHTML = ageInfo.quickPrompts
      .map(
        (q) =>
          `<button class="prompt-pill" onclick="sendQuickPrompt('${q.replace(/'/g, "\\'")}')">${q}</button>`
      )
      .join("");
  }

  window.sendQuickPrompt = function (text) {
    const input = document.getElementById("chat-input");
    input.value = text;
    window.sendChatMessage();
  };

  function renderChatMessages() {
    const box = document.getElementById("chat-messages");
    if (!box) return;

    if (chatHistory.length === 0) {
      const ageInfo = window.THCS_DATA.ageProfiles[profile.age] || window.THCS_DATA.ageProfiles[14];
      const welcomeHtml = `<p>Chào <strong>${profile.name}</strong>! 🤖 Mình là <strong>banem</strong> — Chatbot tư vấn tâm lý & học đường dành riêng cho học sinh THCS (${ageInfo.age} tuổi - ${ageInfo.grade}).</p>
      <p style="margin-top:6px;">Mọi tâm sự của cậu về <em>áp lực điểm số, thi vào lớp 10, tình bạn, rung động tuổi dậy thì hay chuyện gia đình</em> đều được <strong>banem</strong> lắng nghe kín đáo và không phán xét.</p>`;
      chatHistory.push({
        sender: "bot",
        html: welcomeHtml,
        rawText: "Chào bạn! Mình là banem.",
        followUps: ageInfo.quickPrompts.slice(0, 3),
        time: getCurrentTimeStr(),
        source: "Chatbot banem"
      });
      saveChat();
    }

    box.innerHTML = chatHistory
      .map((msg) => {
        const avatar = msg.sender === "bot" ? (profile.persona === "expert" ? "👩‍🏫" : "🤖") : "🧑‍🎓";
        const followUpHtml =
          msg.sender === "bot" && msg.followUps && msg.followUps.length > 0
            ? `<div class="follow-up-chips">
                ${msg.followUps
                  .map(
                    (f) =>
                      `<button class="follow-up-btn" onclick="sendQuickPrompt('${f.replace(/'/g, "\\'")}')">💬 ${f}</button>`
                  )
                  .join("")}
              </div>`
            : "";

        const crisisBtn =
          msg.isCrisis
            ? `<div style="margin-top:10px;">
                <a href="tel:111" class="call-link-btn">
                  <span>📞 Gọi Tổng đài Bảo vệ Trẻ em 111 (Miễn phí)</span>
                  <span>Gọi ngay ➔</span>
                </a>
              </div>`
            : "";

        return `
          <div class="msg-row ${msg.sender}">
            <div class="msg-avatar">${avatar}</div>
            <div style="flex:1;max-width:100%;">
              <div class="msg-bubble">
                ${msg.html}
                ${crisisBtn}
                <div class="msg-meta">
                  <span>${msg.source || ""}</span>
                  <span>${msg.time || ""}</span>
                </div>
              </div>
              ${followUpHtml}
            </div>
          </div>
        `;
      })
      .join("");

    scrollToBottomChat();
  }

  function scrollToBottomChat() {
    const box = document.getElementById("chat-messages");
    if (box) {
      setTimeout(() => {
        box.scrollTop = box.scrollHeight;
      }, 60);
    }
  }

  function getCurrentTimeStr() {
    const now = new Date();
    return now.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
  }

  window.sendChatMessage = async function () {
    const input = document.getElementById("chat-input");
    const text = (input.value || "").trim();
    if (!text) return;

    input.value = "";
    chatHistory.push({
      sender: "user",
      html: `<p>${escapeHtml(text)}</p>`,
      rawText: text,
      time: getCurrentTimeStr(),
      source: profile.name
    });
    saveChat();
    renderChatMessages();

    // Show typing indicator
    const box = document.getElementById("chat-messages");
    const typingEl = document.createElement("div");
    typingEl.className = "msg-row bot";
    typingEl.id = "typing-indicator";
    typingEl.innerHTML = `
      <div class="msg-avatar">${profile.persona === "expert" ? "👩‍🏫" : "🤖"}</div>
      <div class="msg-bubble"><em>banem đang lắng nghe và suy nghĩ câu trả lời cho cậu...</em></div>
    `;
    box.appendChild(typingEl);
    scrollToBottomChat();

    const reply = await window.AICounselor.generateReply(
      text,
      {
        age: profile.age,
        name: profile.name,
        persona: profile.persona
      },
      chatHistory
    );

    const indicator = document.getElementById("typing-indicator");
    if (indicator) indicator.remove();

    chatHistory.push({
      sender: "bot",
      html: reply.html,
      rawText: text,
      followUps: reply.followUps || [],
      isCrisis: reply.isCrisis,
      time: getCurrentTimeStr(),
      source: reply.source
    });
    saveChat();
    renderChatMessages();
  };

  window.clearChatHistory = function () {
    chatHistory = [];
    localStorage.removeItem(CHAT_KEY);
    renderChatMessages();
    showToast("Đã làm mới cuộc trò chuyện!");
  };

  // MOOD TRACKER & DIARY MODULE
  window.selectDiaryMood = function (score, emoji, label) {
    selectedMoodScore = score;
    selectedMoodEmoji = emoji;
    selectedMoodLabel = label;
    document.querySelectorAll("#diary-mood-picker .mood-btn").forEach((btn) => {
      btn.classList.toggle("selected", Number(btn.dataset.score) === score);
    });
  };

  window.saveMoodEntry = function () {
    const reason = document.getElementById("diary-reason").value;
    const note = (document.getElementById("diary-note").value || "").trim();
    const now = new Date();

    const entry = {
      id: Date.now(),
      dateStr: now.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" }),
      fullDate: now.toLocaleString("vi-VN"),
      score: selectedMoodScore,
      emoji: selectedMoodEmoji,
      label: selectedMoodLabel,
      reason: reason,
      note: note || "Không có ghi chú thêm."
    };

    moodLogs.unshift(entry);
    saveMoods();
    document.getElementById("diary-note").value = "";
    renderMoodSection();
    showToast("Đã lưu vào Nhật ký cảm xúc an toàn! 💙");
  };

  window.unlockDiaryWithPin = function () {
    const inputPin = (document.getElementById("pin-unlock-input").value || "").trim();
    if (inputPin === profile.diaryPin) {
      diaryUnlocked = true;
      renderMoodSection();
      showToast("Đã mở khóa Nhật ký riêng tư!");
    } else {
      showToast("Mã PIN chưa đúng, cậu thử lại nhé!");
    }
  };

  function renderMoodSection() {
    const lockView = document.getElementById("diary-locked-view");
    const contentView = document.getElementById("diary-unlocked-view");

    if (profile.diaryPin && !diaryUnlocked) {
      lockView.style.display = "block";
      contentView.style.display = "none";
      return;
    }
    lockView.style.display = "none";
    contentView.style.display = "block";

    // Render 7-day chart
    const chartBox = document.getElementById("mood-chart-box");
    const recent7 = moodLogs.slice(0, 7).reverse();
    if (recent7.length === 0) {
      chartBox.innerHTML = `<p style="font-size:13px;color:var(--text-muted);margin:auto;">Chưa có dữ liệu cảm xúc. Hãy lưu cảm xúc đầu tiên của cậu hôm nay nhé!</p>`;
    } else {
      chartBox.innerHTML = recent7
        .map((item) => {
          const heightPx = Math.max(18, item.score * 16);
          return `
            <div class="mood-bar-col">
              <span style="font-size:16px;">${item.emoji}</span>
              <div class="mood-bar" style="height:${heightPx}px;"></div>
              <span style="font-size:10px;color:var(--text-muted);">${item.dateStr}</span>
            </div>
          `;
        })
        .join("");
    }

    // Render entries list
    const listEl = document.getElementById("mood-history-list");
    if (moodLogs.length === 0) {
      listEl.innerHTML = `<p style="font-size:13px;color:var(--text-muted);text-align:center;padding:12px;">Nhật ký của cậu đang trống.</p>`;
    } else {
      listEl.innerHTML = moodLogs
        .slice(0, 15)
        .map(
          (item) => `
          <div style="border-bottom:1px solid var(--border-color);padding:10px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <strong style="font-size:13.5px;">${item.emoji} ${item.label} • <span style="color:var(--primary);">${item.reason}</span></strong>
              <span style="font-size:11px;color:var(--text-muted);">${item.fullDate}</span>
            </div>
            <p style="font-size:13px;margin-top:4px;color:var(--text-main);">${escapeHtml(item.note)}</p>
          </div>
        `
        )
        .join("");
    }
  }

  // BREATHING 4-7-8 & WEB AUDIO SYNTHESIZER
  window.toggleBreathing = function () {
    const btn = document.getElementById("btn-start-breath");
    const circle = document.getElementById("breath-circle");
    const textEl = document.getElementById("breath-status-text");

    if (isBreathing) {
      stopBreathingCycle();
      btn.textContent = "▶️ Bắt đầu Hít thở 4-7-8";
      circle.className = "breath-circle";
      textEl.textContent = "Sẵn sàng thư giãn";
      return;
    }

    isBreathing = true;
    btn.textContent = "⏹️ Dừng bài tập thở";

    function runOneCycle() {
      if (!isBreathing) return;
      // Inhale 4s
      circle.className = "breath-circle inhale";
      textEl.innerHTML = "Hít vào bằng mũi...<br><span style='font-size:20px;'>4 giây</span>";
      playSoftChime(432, 0.3);

      const t1 = setTimeout(() => {
        if (!isBreathing) return;
        // Hold 7s
        circle.className = "breath-circle hold";
        textEl.innerHTML = "Giữ nhịp thở...<br><span style='font-size:20px;'>7 giây</span>";
        playSoftChime(528, 0.25);
      }, 4000);

      const t2 = setTimeout(() => {
        if (!isBreathing) return;
        // Exhale 8s
        circle.className = "breath-circle exhale";
        textEl.innerHTML = "Thở ra từ từ bằng miệng...<br><span style='font-size:20px;'>8 giây</span>";
        playSoftChime(396, 0.35);
      }, 11000);

      breathTimeouts.push(t1, t2);
    }

    runOneCycle();
    breathInterval = setInterval(runOneCycle, 19000);
  };

  function stopBreathingCycle() {
    isBreathing = false;
    if (breathInterval) clearInterval(breathInterval);
    breathTimeouts.forEach((t) => clearTimeout(t));
    breathTimeouts = [];
  }

  function playSoftChime(freq, duration) {
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;
      if (!audioCtx) audioCtx = new AudioContextClass();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + duration);
    } catch (e) {}
  }

  window.toggleAmbientSound = function () {
    const btn = document.getElementById("btn-ambient-sound");
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;
      if (!audioCtx) audioCtx = new AudioContextClass();

      if (isAmbientPlaying && ambientNode) {
        ambientNode.stop();
        ambientNode = null;
        isAmbientPlaying = false;
        btn.textContent = "🌧️ Bật tiếng mưa & sóng thư giãn (Offline)";
        return;
      }

      // Generate soothing pink/brown noise waves (rain/ocean sound 100% offline)
      const bufferSize = audioCtx.sampleRate * 3;
      const noiseBuffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
      const output = noiseBuffer.getChannelData(0);
      let lastOut = 0.0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        output[i] = (lastOut + 0.02 * white) / 1.02;
        lastOut = output[i];
        output[i] *= 0.12;
      }

      const whiteNoise = audioCtx.createBufferSource();
      whiteNoise.buffer = noiseBuffer;
      whiteNoise.loop = true;

      const filter = audioCtx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.value = 650;

      whiteNoise.connect(filter);
      filter.connect(audioCtx.destination);
      whiteNoise.start();

      ambientNode = whiteNoise;
      isAmbientPlaying = true;
      btn.textContent = "🔇 Tắt âm thanh thư giãn";
      showToast("Đang phát âm thanh sóng & mưa dịu nhẹ 🌧️");
    } catch (e) {
      showToast("Thiết bị không hỗ trợ bộ tạo âm thanh.");
    }
  };

  // POMODORO & WORRY BOX
  window.togglePomodoro = function () {
    const btn = document.getElementById("btn-pomo-toggle");
    if (pomoRunning) {
      clearInterval(pomoTimer);
      pomoRunning = false;
      btn.textContent = "▶️ Tiếp tục";
      return;
    }
    pomoRunning = true;
    btn.textContent = "⏸️ Tạm dừng";
    pomoTimer = setInterval(() => {
      if (pomoSeconds > 0) {
        pomoSeconds--;
        updatePomoDisplay();
      } else {
        clearInterval(pomoTimer);
        pomoRunning = false;
        btn.textContent = "▶️ Bắt đầu 25 phút";
        playSoftChime(660, 0.8);
        showToast("🎉 Hoàn thành 1 phiên tập trung Pomodoro! Nghỉ giải lao 5 phút nhé!");
      }
    }, 1000);
  };

  window.resetPomodoro = function (minutes) {
    clearInterval(pomoTimer);
    pomoRunning = false;
    pomoSeconds = (minutes || 25) * 60;
    updatePomoDisplay();
    document.getElementById("btn-pomo-toggle").textContent = "▶️ Bắt đầu";
  };

  function updatePomoDisplay() {
    const m = String(Math.floor(pomoSeconds / 60)).padStart(2, "0");
    const s = String(pomoSeconds % 60).padStart(2, "0");
    const el = document.getElementById("pomo-timer-display");
    if (el) el.textContent = `${m}:${s}`;
  }

  window.releaseWorryToUniverse = function () {
    const input = document.getElementById("worry-box-input");
    const val = (input.value || "").trim();
    if (!val) {
      showToast("Cậu hãy viết điều làm cậu buồn vào ô trước nhé!");
      return;
    }
    input.style.transition = "all 0.6s ease";
    input.style.transform = "scale(0.85)";
    input.style.opacity = "0";
    playSoftChime(528, 0.5);
    setTimeout(() => {
      input.value = "";
      input.style.transform = "scale(1)";
      input.style.opacity = "1";
      showToast("✨ Nỗi buồn đã hóa thành bụi sao bay vào vũ trụ! Cậu sẽ ổn thôi!");
    }, 650);
  };

  // QUIZZES MODULE
  function renderQuizList() {
    const listView = document.getElementById("quiz-list-view");
    const playView = document.getElementById("quiz-play-view");
    listView.style.display = "block";
    playView.style.display = "none";

    const container = document.getElementById("quiz-cards-container");
    container.innerHTML = window.THCS_DATA.quizzes
      .map(
        (qz) => `
        <div class="quiz-card">
          <span class="quiz-badge" style="background:${qz.badgeColor}20;color:${qz.badgeColor};">${qz.badge}</span>
          <h3 style="font-size:15.5px;font-weight:700;">${qz.title}</h3>
          <p style="font-size:13px;color:var(--text-muted);">${qz.description}</p>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;">
            <span style="font-size:12px;font-weight:600;color:var(--text-muted);">📋 ${qz.questions.length} câu hỏi tình huống</span>
            <button class="btn-primary" onclick="startQuiz('${qz.id}')">Làm bài ngay ➔</button>
          </div>
        </div>
      `
      )
      .join("");
  }

  window.startQuiz = function (quizId) {
    activeQuiz = window.THCS_DATA.quizzes.find((q) => q.id === quizId);
    if (!activeQuiz) return;
    activeQuizIndex = 0;
    activeQuizAnswers = [];

    document.getElementById("quiz-list-view").style.display = "none";
    document.getElementById("quiz-play-view").style.display = "block";
    renderActiveQuizQuestion();
  };

  function renderActiveQuizQuestion() {
    const qObj = activeQuiz.questions[activeQuizIndex];
    const total = activeQuiz.questions.length;
    const progressPct = Math.round(((activeQuizIndex + 1) / total) * 100);

    const box = document.getElementById("quiz-play-content");
    box.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-size:12px;font-weight:700;color:var(--primary);">Câu ${activeQuizIndex + 1} / ${total}</span>
        <button class="btn-secondary" style="padding:5px 10px;font-size:12px;" onclick="BackToQuizList()">✕ Thoát</button>
      </div>
      <div style="height:6px;background:var(--bg-subtle);border-radius:99px;overflow:hidden;margin-bottom:14px;">
        <div style="height:100%;width:${progressPct}%;background:var(--primary);transition:width 0.25s;"></div>
      </div>
      <h3 style="font-size:15.5px;margin-bottom:14px;line-height:1.45;">${qObj.q}</h3>
      <div>
        ${qObj.options
          .map(
            (opt, idx) => `
            <button class="quiz-option-btn" onclick="answerQuizQuestion(${idx})">
              ${opt.text}
            </button>
          `
          )
          .join("")}
      </div>
    `;
  }

  window.answerQuizQuestion = function (optionIndex) {
    const qObj = activeQuiz.questions[activeQuizIndex];
    activeQuizAnswers.push(qObj.options[optionIndex]);

    if (activeQuizIndex + 1 < activeQuiz.questions.length) {
      activeQuizIndex++;
      renderActiveQuizQuestion();
    } else {
      finishActiveQuiz();
    }
  };

  function finishActiveQuiz() {
    const box = document.getElementById("quiz-play-content");
    let resultTitle = "";
    let resultDesc = "";
    let extraAdvice = "";

    if (activeQuiz.scoreRanges) {
      const totalScore = activeQuizAnswers.reduce((acc, item) => acc + (item.score || 0), 0);
      const matchedRange =
        activeQuiz.scoreRanges.find((r) => totalScore >= r.min && totalScore <= r.max) ||
        activeQuiz.scoreRanges[0];
      resultTitle = matchedRange.title;
      resultDesc = matchedRange.desc;
      extraAdvice = `<p style="margin-top:10px;"><strong>💡 Lời khuyên dành cho cậu:</strong> ${matchedRange.advice}</p>`;
    } else if (activeQuiz.results) {
      const counts = {};
      activeQuizAnswers.forEach((ans) => {
        counts[ans.type] = (counts[ans.type] || 0) + 1;
      });
      let topType = Object.keys(counts)[0];
      for (const k in counts) {
        if (counts[k] > counts[topType]) topType = k;
      }
      const resObj = activeQuiz.results[topType];
      resultTitle = resObj.title;
      resultDesc = resObj.desc;
      extraAdvice = `
        <div style="margin-top:10px;padding:12px;background:var(--bg-subtle);border-radius:12px;">
          <p><strong>📚 ${resObj.subjects}</strong></p>
          ${resObj.pathway ? `<p style="margin-top:6px;"><strong>🧭 ${resObj.pathway}</strong></p>` : ""}
        </div>
      `;
    }

    quizHistory.unshift({
      quizTitle: activeQuiz.title,
      resultTitle: resultTitle,
      date: new Date().toLocaleDateString("vi-VN")
    });
    localStorage.setItem(QUIZ_HISTORY_KEY, JSON.stringify(quizHistory.slice(0, 20)));

    const askPrompt = `Mình vừa làm bài '${activeQuiz.title}' và đạt kết quả là '${resultTitle}'. Tư vấn chi tiết hơn giúp mình nhé!`;

    box.innerHTML = `
      <div style="text-align:center;padding:8px 0;">
        <div style="font-size:40px;margin-bottom:6px;">🎉</div>
        <span class="quiz-badge" style="background:rgba(79,70,229,0.12);color:var(--primary);">Kết quả khám phá bản thân</span>
        <h3 style="font-size:18px;margin:10px 0;color:var(--primary);">${resultTitle}</h3>
      </div>
      <p style="font-size:14px;line-height:1.55;">${resultDesc}</p>
      ${extraAdvice}
      <div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap;">
        <button class="btn-primary" style="flex:1;" onclick="askFromHome('${askPrompt.replace(/'/g, "\\'")}')">💬 Hỏi sâu hơn với Chatbot banem</button>
        <button class="btn-secondary" onclick="BackToQuizList()">Làm bài khác</button>
      </div>
    `;
  }

  window.BackToQuizList = function () {
    renderQuizList();
  };

  // HANDBOOK MODULE
  let activeHandbookFilter = "all";

  window.filterHandbook = function (ageFilter) {
    activeHandbookFilter = ageFilter;
    document.querySelectorAll("#handbook-filter-bar .sub-tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.agefilter === ageFilter);
    });
    renderHandbook();
  };

  function renderHandbook() {
    const container = document.getElementById("handbook-list");
    if (!container) return;

    const articles = window.THCS_DATA.handbookArticles.filter((a) => {
      if (activeHandbookFilter === "all") return true;
      return a.ageGroup === activeHandbookFilter;
    });

    container.innerHTML = articles
      .map(
        (art) => `
        <div class="card">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="font-size:22px;">${art.icon}</span>
            <span class="quiz-badge" style="background:rgba(79,70,229,0.12);color:var(--primary);">${art.category}</span>
          </div>
          <h3 style="font-size:15.5px;margin-bottom:6px;">${art.title}</h3>
          <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px;">${art.summary}</p>
          <div style="font-size:13.5px;line-height:1.55;margin-bottom:12px;">
            ${art.content.map((p) => `<p style="margin-bottom:6px;">${formatBold(p)}</p>`).join("")}
          </div>
          ${
            art.scenario
              ? `<div style="background:var(--bg-subtle);padding:12px;border-radius:14px;border-left:3px solid var(--primary);">
                  <p style="font-size:13px;font-weight:700;margin-bottom:8px;">🤔 ${art.scenario.question}</p>
                  ${art.scenario.options
                    .map(
                      (opt, idx) => `
                      <button class="quiz-option-btn" style="background:var(--bg-card);font-size:12.5px;padding:9px 12px;" onclick="showScenarioFeedback('${art.id}', ${idx})">
                        Phương án ${idx + 1}: ${opt.label}
                      </button>
                    `
                    )
                    .join("")}
                  <div id="scenario-fb-${art.id}" style="display:none;margin-top:8px;font-size:12.5px;padding:8px 10px;border-radius:10px;background:rgba(16,185,129,0.12);color:var(--text-main);"></div>
                </div>`
              : ""
          }
        </div>
      `
      )
      .join("");
  }

  window.showScenarioFeedback = function (artId, optIdx) {
    const art = window.THCS_DATA.handbookArticles.find((a) => a.id === artId);
    if (!art || !art.scenario) return;
    const fbEl = document.getElementById(`scenario-fb-${artId}`);
    if (!fbEl) return;
    fbEl.style.display = "block";
    fbEl.innerHTML = `<strong>Phân tích tâm lý:</strong> ${art.scenario.options[optIdx].feedback}`;
  };

  // MODALS (SOS & SETTINGS)
  window.openModal = function (id) {
    const el = document.getElementById(id);
    if (el) el.classList.add("open");

    if (id === "modal-settings") {
      document.getElementById("set-student-name").value = profile.name || "";
      document.getElementById("set-student-age").value = String(profile.age || 14);
      document.getElementById("set-gemini-key").value = localStorage.getItem("thcs_gemini_api_key") || "";
      document.getElementById("set-parent-phone").value = profile.parentPhone || "";
      document.getElementById("set-diary-pin").value = profile.diaryPin || "";
    } else if (id === "modal-sos") {
      renderCustomTrustedContacts();
    }
  };

  window.closeModal = function (id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove("open");
  };

  window.saveAppSettings = function () {
    const newName = (document.getElementById("set-student-name").value || "").trim() || "Bạn nhỏ";
    const newAge = Number(document.getElementById("set-student-age").value || 14);
    const apiKey = (document.getElementById("set-gemini-key").value || "").trim();
    const parentPhone = (document.getElementById("set-parent-phone").value || "").trim();
    const diaryPin = (document.getElementById("set-diary-pin").value || "").trim();

    profile.name = newName;
    profile.age = newAge;
    profile.parentPhone = parentPhone;
    profile.diaryPin = diaryPin;
    saveProfile();

    if (apiKey) {
      localStorage.setItem("thcs_gemini_api_key", apiKey);
    } else {
      localStorage.removeItem("thcs_gemini_api_key");
    }

    renderHomeAgeContent();
    renderChatQuickPrompts();
    closeModal("modal-settings");
    showToast("Đã lưu cài đặt hồ sơ thành công! ✨");
  };

  function renderCustomTrustedContacts() {
    const box = document.getElementById("trusted-contact-box");
    if (!box) return;
    if (profile.parentPhone) {
      box.innerHTML = `
        <a href="tel:${escapeHtml(profile.parentPhone)}" class="call-link-btn" style="background:#4f46e5;margin-top:8px;">
          <span>👨‍👩‍👧 Gọi Người thân / Giáo viên tin cậy (${escapeHtml(profile.parentPhone)})</span>
          <span>Gọi ➔</span>
        </a>
      `;
    } else {
      box.innerHTML = `<p style="font-size:12px;color:var(--text-muted);margin-top:6px;">💡 Cậu có thể thêm số điện thoại Bố/Mẹ hoặc Thầy/Cô chủ nhiệm trong phần ⚙️ Cài đặt để gọi nhanh khi khẩn cấp.</p>`;
    }
  }

  window.toggleTheme = function () {
    profile.theme = profile.theme === "dark" ? "light" : "dark";
    saveProfile();
    applyTheme();
  };

  window.sendCounselingEmail = function () {
    const infoEl = document.getElementById("mail-student-info");
    const contentEl = document.getElementById("mail-student-content");
    const studentInfo = (infoEl?.value || "").trim() || `${profile.name} (${profile.age} tuổi)`;
    const content = (contentEl?.value || "").trim();

    if (!content) {
      showToast("Em hãy nhập nội dung tâm sự hoặc câu hỏi trước khi gửi nhé!");
      return;
    }

    const teacherEmail = "hoangthcsphuhuu@gmail.com";
    const subject = `[Tư vấn Học đường THCS Phú Hữu] Tâm sự từ: ${studentInfo}`;
    const body = `Kính gửi Thầy/Cô Tổ Tư vấn Tâm lý Học đường - Trường THCS Phú Hữu,\n\n- Học sinh gửi: ${studentInfo}\n- Độ tuổi/Khối lớp: ${profile.age} tuổi (${window.THCS_DATA.ageProfiles[profile.age]?.grade || "THCS"})\n\nNội dung cần chia sẻ / hỗ trợ:\n${content}\n\n---\nGửi từ Ứng dụng Bạn Đồng Hành THCS`;

    const mailtoUrl = `mailto:${teacherEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = mailtoUrl;
    showToast("Đang mở ứng dụng Email để gửi tới hoangthcsphuhuu@gmail.com!");
  };

  window.installPWA = async function () {
    if (deferredInstallPrompt) {
      deferredInstallPrompt.prompt();
      const { outcome } = await deferredInstallPrompt.userChoice;
      if (outcome === "accepted") {
        showToast("Đang cài đặt ứng dụng lên màn hình chính!");
      }
      deferredInstallPrompt = null;
    } else {
      showToast("Trên điện thoại Android: Bấm menu trình duyệt (⋮) ➔ 'Thêm vào màn hình chính' hoặc cài bằng file APK!");
    }
  };

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatBold(str) {
    return str.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
  }

  // Initialize App on DOMContentLoaded
  document.addEventListener("DOMContentLoaded", () => {
    loadState();
    applyTheme();
    renderHomeAgeContent();
    window.refreshDailyQuote();
    renderChatQuickPrompts();
    renderChatMessages();
    renderMoodSection();
    renderQuizList();
    renderHandbook();

    const chatInput = document.getElementById("chat-input");
    if (chatInput) {
      chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          window.sendChatMessage();
        }
      });
    }

    window.addEventListener("beforeinstallprompt", (e) => {
      e.preventDefault();
      deferredInstallPrompt = e;
      const installBanner = document.getElementById("pwa-install-banner");
      if (installBanner) installBanner.style.display = "flex";
    });

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("./sw.js").catch(() => {});
    }
  });
})();
