// Bộ não Trợ lý Tư vấn Tâm lý Lai (Hybrid Offline Expert + Google Gemini AI)

window.AICounselor = (function () {
  function removeVietnameseTones(str) {
    return str
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase();
  }

  function adaptPronouns(text, persona, studentName) {
    const nameCall = studentName ? studentName : (persona === "expert" ? "em" : "cậu");
    if (persona === "expert") {
      return text
        .replace(/\bMình\b/g, "Anh/Chị")
        .replace(/\bmình\b/g, "anh/chị")
        .replace(/\bCậu\b/g, "Em")
        .replace(/\bcậu\b/g, "em")
        .replace(/\bchúng mình\b/g, "chúng ta");
    }
    return text.replace(/\{name\}/g, nameCall);
  }

  function matchKnowledgeTopic(userMessage) {
    const rawLower = userMessage.toLowerCase().trim();
    const noTone = removeVietnameseTones(rawLower);
    const topics = window.THCS_DATA.counselingKnowledge;

    let bestTopic = null;
    let highestScore = 0;

    for (const topic of topics) {
      let matchCount = 0;
      for (const kw of topic.keywords) {
        const kwLower = kw.toLowerCase();
        const kwNoTone = removeVietnameseTones(kwLower);
        if (rawLower.includes(kwLower) || noTone.includes(kwNoTone)) {
          matchCount += 1;
        }
      }
      if (matchCount > 0) {
        const totalScore = matchCount * 20 + (topic.priority || 50);
        if (totalScore > highestScore) {
          highestScore = totalScore;
          bestTopic = topic;
        }
      }
    }

    return bestTopic;
  }

  function buildOfflineResponse(userMessage, context) {
    const { age = 14, name = "bạn", persona = "may" } = context;
    const rawLower = userMessage.toLowerCase().trim();
    const noTone = removeVietnameseTones(rawLower);

    // 1. Check matched specialized counseling topic
    const matched = matchKnowledgeTopic(userMessage);
    if (matched) {
      let ageNote = "";
      if (age == 13) {
        ageNote = "Ở tuổi 13 (Lớp 7), cậu mới bước vào giai đoạn đầu dậy thì nên những cảm xúc này lại càng nhạy cảm hơn.";
      } else if (age == 14) {
        ageNote = "Ở tuổi 14 (Lớp 8), đây là lúc cậu đang định hình cá tính riêng nên những trăn trở này rất phổ biến.";
      } else if (age == 15) {
        ageNote = "Ở tuổi 15 (Lớp 9), áp lực cuối cấp THCS đôi khi làm mọi chuyện trở nên nặng nề hơn bình thường.";
      }

      const bulletHtml = matched.advice
        .map((item) => `<li>${formatMarkdownInline(adaptPronouns(item, persona, name))}</li>`)
        .join("");

      const replyHtml = `
        <p>${formatMarkdownInline(adaptPronouns(matched.empathy, persona, name))}</p>
        <p style="margin-top:6px;font-size:12.5px;opacity:0.88;"><em>💡 ${adaptPronouns(ageNote, persona, name)}</em></p>
        <ul style="margin-top:8px;">${bulletHtml}</ul>
      `;

      return {
        html: replyHtml,
        followUps: matched.followUps.map((f) => adaptPronouns(f, persona, name)),
        isCrisis: !!matched.isCrisis,
        source: "Bộ não Tâm lý Học đường THCS"
      };
    }

    // 2. Greeting / Small talk detection
    if (
      /^(xin chao|chao|hi|hello|alo|hey|chao banem|chao may|chao chi|chao anh)\b/.test(noTone) ||
      rawLower.length <= 6
    ) {
      const greetText =
        persona === "expert"
          ? `Chào **${name}**! Anh/Chị là Chuyên gia Tư vấn Tâm lý Học đường dành cho lứa tuổi ${age} (${window.THCS_DATA.ageProfiles[age]?.grade || "THCS"}). Hôm nay ở trường hay ở nhà có chuyện gì làm em bận tâm không? Hãy kể cho anh/chị nghe nhé!`
          : `Chào **${name}** nha! 🤖 Mình là **banem** — người bạn đồng hành lắng nghe mọi tâm sự tuổi ${age} (${window.THCS_DATA.ageProfiles[age]?.grade || "THCS"}) của cậu. Hôm nay cậu cảm thấy thế nào? Có chuyện vui hay nỗi buồn nào muốn kể cho **banem** nghe không?`;
      return {
        html: `<p>${formatMarkdownInline(greetText)}</p>`,
        followUps: window.THCS_DATA.ageProfiles[age]?.quickPrompts.slice(0, 3) || [],
        isCrisis: false,
        source: "Chatbot banem • THCS"
      };
    }

    // 3. General sadness / stress / feeling down detection
    if (
      noTone.includes("buon") ||
      noTone.includes("met") ||
      noTone.includes("khoc") ||
      noTone.includes("co don") ||
      noTone.includes("ap luc") ||
      noTone.includes("stress") ||
      noTone.includes("nan") ||
      noTone.includes("chan")
    ) {
      const comfort = `Cảm ơn **${name}** đã tin tưởng chia sẻ với mình nhé! 🫂 Khi ở tuổi ${age}, có những ngày cậu cảm thấy mệt mỏi, buồn bã hay trống rỗng mà chưa gọi tên rõ được nguyên nhân.
      <ul>
        <li><strong>Cho phép bản thân được nghỉ ngơi:</strong> Cậu không cần phải tỏ ra mạnh mẽ 100% thời gian. Hãy uống một cốc nước ấm và hít thở sâu nhé.</li>
        <li><strong>Tìm nguyên nhân gốc rễ:</strong> Nỗi buồn hôm nay của cậu đến nhiều nhất từ <em>chuyện học tập điểm số</em>, <em>chuyện bạn bè trên lớp</em> hay <em>chuyện gia đình</em>?</li>
        <li><strong>Góc Chữa Lành:</strong> Cậu có thể bấm sang mục <strong>Chữa lành</strong> để tập thở 4-7-8 hoặc viết nỗi buồn vào hộp thư vũ trụ để nhẹ lòng hơn nha!</li>
      </ul>`;
      return {
        html: adaptPronouns(comfort, persona, name),
        followUps: [
          "Mình buồn vì chuyện học tập và điểm số",
          "Mình buồn vì chuyện bạn bè ở lớp",
          "Mình buồn vì bố mẹ không hiểu mình"
        ].map((f) => adaptPronouns(f, persona, name)),
        isCrisis: false,
        source: "Bộ não Tâm lý Học đường THCS"
      };
    }

    // 4. Intelligent empathetic fallback asking guiding questions tailored to age 13-15
    const fallbackText = `Mình đang lắng nghe **${name}** đây! 💙 Câu chuyện cậu vừa chia sẻ rất đáng để chúng mình cùng suy ngẫm ở lứa tuổi ${age} (${window.THCS_DATA.ageProfiles[age]?.grade}).
    <ul>
      <li>Cậu có thể kể rõ hơn một chút cho mình biết <strong>điều gì trong chuyện này làm cậu lo lắng hoặc khó xử nhất</strong> lúc này không?</li>
      <li>Hoặc cậu có thể chọn một trong các khía cạnh bên dưới để mình tư vấn sát nhất cho cậu nhé:</li>
    </ul>`;

    return {
      html: adaptPronouns(fallbackText, persona, name),
      followUps: (window.THCS_DATA.ageProfiles[age]?.quickPrompts || []).slice(0, 3),
      isCrisis: false,
      source: "Bộ não Tâm lý Học đường THCS"
    };
  }

  function formatMarkdownInline(text) {
    if (!text) return "";
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/\n/g, "<br>");
  }

  async function callGeminiAPI(userMessage, context, apiKey, chatHistory) {
    const { age = 14, name = "Bạn", persona = "may" } = context;
    const grade = window.THCS_DATA.ageProfiles[age]?.grade || "THCS";
    const roleDesc =
      persona === "expert"
        ? "Chuyên gia Tham vấn Tâm lý Học đường THCS tên là 'banem' (xưng 'Anh/Chị' - gọi học sinh là 'Em' hoặc tên học sinh)"
        : "Chatbot đồng hành tâm lý tên là 'banem' (xưng 'Mình' hoặc 'banem' - gọi học sinh là 'Cậu' hoặc tên học sinh)";

    const systemInstruction = `Bạn là ${roleDesc}, chuyên tư vấn tâm lý, kỹ năng sống, phương pháp học tập và định hướng phân luồng sau THCS cho học sinh Trung học cơ sở tại Việt Nam, đặc biệt ở độ tuổi 13, 14, 15 (Lớp 7, Lớp 8, Lớp 9).
Thông tin học sinh đang trò chuyện:
- Tên/Biệt danh: ${name}
- Độ tuổi hiện tại: ${age} tuổi (${grade})

Nguyên tắc tư vấn BẮT BUỘC:
1. Luôn giới thiệu tên mình là "banem" khi học sinh hỏi tên. Thấu cảm, ấm áp, tôn trọng, tuyệt đối không phán xét hay dạy đời.
2. Ngôn ngữ trong sáng, gần gũi với học sinh THCS Việt Nam (13-15 tuổi), trình bày rõ ràng thành các ý dễ đọc (dùng gạch đầu dòng ngắn gọn).
3. Đưa ra giải pháp thực tế, an toàn, phù hợp môi trường học đường và gia đình Việt Nam.
4. Nếu phát hiện dấu hiệu tự làm hại bản thân, tự tử, bạo lực nghiêm trọng hoặc xâm hại: Phải ưu tiên trấn an tinh thần và hướng dẫn gọi ngay Tổng đài Quốc gia Bảo vệ Trẻ em 111 (miễn phí 24/7) hoặc báo cho cha mẹ, thầy cô.`;

    const recentContents = (chatHistory || []).slice(-6).map((msg) => ({
      role: msg.sender === "user" ? "user" : "model",
      parts: [{ text: msg.rawText || msg.text || "" }]
    }));

    recentContents.push({
      role: "user",
      parts: [{ text: userMessage }]
    });

    const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${encodeURIComponent(apiKey)}`;

    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: systemInstruction }] },
        contents: recentContents,
        generationConfig: {
          temperature: 0.7,
          maxOutputTokens: 700
        }
      })
    });

    if (!response.ok) {
      throw new Error(`Gemini API HTTP ${response.status}`);
    }

    const data = await response.json();
    const replyText =
      data?.candidates?.[0]?.content?.parts?.[0]?.text ||
      "Mình luôn ở đây lắng nghe cậu!";

    return {
      html: `<p>${formatMarkdownInline(replyText)}</p>`,
      followUps: (window.THCS_DATA.ageProfiles[age]?.quickPrompts || []).slice(0, 2),
      isCrisis: false,
      source: "Gemini AI Trực tuyến"
    };
  }

  async function generateReply(userMessage, context, chatHistory) {
    // Always check crisis safety keywords first
    const matched = matchKnowledgeTopic(userMessage);
    if (matched && matched.isCrisis) {
      return buildOfflineResponse(userMessage, context);
    }

    const apiKey = (localStorage.getItem("thcs_gemini_api_key") || "").trim();
    if (apiKey && navigator.onLine) {
      try {
        return await callGeminiAPI(userMessage, context, apiKey, chatHistory);
      } catch (err) {
        console.warn("Fallback to Offline Counseling Engine:", err);
      }
    }

    // Simulate natural thinking delay for offline counselor
    await new Promise((resolve) => setTimeout(resolve, 420));
    return buildOfflineResponse(userMessage, context);
  }

  return {
    generateReply
  };
})();
