# CmartBridge Rwanda — WhatsApp Templates

Load these as **Quick Replies** in WhatsApp Business (`/paid`, `/bought`, `/shipped`, `/arrived`, `/delivery` …). Every order gets all five status updates — no exceptions, even for friends. `{placeholders}` get filled per order. Kinyarwanda drafts should be reviewed by a native speaker before launch.

---

## The 5 status updates

### 1️⃣ Payment received — `/paid`

**EN**
> ✅ *Payment received — Murakoze {name}!*
> We've received **{amount} RWF** for: {item}.
> This is your all-in price — product, shipping, customs and VAT included. Nothing more to pay at delivery.
> Next: we buy your item in Korea this **{buying_day}** and send you a photo of it. Delivery: 2–4 weeks. 🇰🇷→🇷🇼

**RW**
> ✅ *Twakiriye ubwishyu — Murakoze {name}!*
> Twakiriye **{amount} RWF** kuri: {item}.
> Iki ni igiciro kirimo byose — igicuruzwa, ubwikorezi n'imisoro. Nta kindi uzishyura.
> Ikurikira: tukigurira mu Bukoreya kuri **{buying_day}** tukakwoherereza ifoto yacyo. Bikugeraho mu byumweru 2–4. 🇰🇷→🇷🇼

### 2️⃣ Purchased, with photo — `/bought`

**EN** *(attach photo of the actual item)*
> 🛍️ *Bought! Here is your item.*
> {name}, this is **your** {item}, bought today in {store, e.g. Olive Young, Seoul} and quality-checked by us in person. 📸
> It ships in this week's batch to Kigali — tracking number coming next.

**RW**
> 🛍️ *Twakiguriye! Dore igicuruzwa cyawe.*
> {name}, iyi ni **iyawe** {item}, tuyiguze uyu munsi muri {store} kandi twayigenzuye ubwacu. 📸
> Yoherezwa muri iyi paki y'iki cyumweru ijya i Kigali — nimero yo kuyikurikirana iraza vuba.

### 3️⃣ Shipped, with tracking — `/shipped`

**EN**
> ✈️ *Your order is on its way to Kigali!*
> Tracking number: **{tracking_no}** (Korea Post EMS — track at ems.epost.go.kr or 17track.net).
> Typical transit: 1–3 weeks. We track it daily and will message you the moment it lands. Every shipment is insured by our promise: lost or damaged = reship or full refund.

**RW**
> ✈️ *Ibyo watumije biri mu nzira bijya i Kigali!*
> Nimero yo gukurikirana: **{tracking_no}** (Korea Post EMS — kurikirana kuri ems.epost.go.kr cyangwa 17track.net).
> Bisanzwe bimara ibyumweru 1–3. Turabikurikirana buri munsi; nibigera i Kigali turakumenyesha ako kanya. Bibuze cyangwa byangiritse = turabisubiza cyangwa tukagusubiza amafaranga yose.

### 4️⃣ Arrived in Kigali — `/arrived`

**EN**
> 🛬 *Your order has landed in Kigali!*
> It's now going through customs clearance with RRA — we handle all of that, it's already included in your price.
> Expected release: {clearance_days} working days. Then we'll arrange delivery. Almost there! 🎉

**RW**
> 🛬 *Ibyo watumije byageze i Kigali!*
> Ubu biri gukorerwa ibya gasutamo (RRA) — ibyo byose ni twe tubikora, kandi biri mu giciro wishyuye.
> Biteganyijwe gusohoka mu minsi {clearance_days} y'akazi. Hanyuma tugategura kubikugezaho. Hasigaye gato! 🎉

### 5️⃣ Cleared / out for delivery — `/delivery`

**EN**
> 🏠 *Out for delivery!*
> {name}, your {item} has cleared customs and {courier_name} will deliver it **{delivery_day}** to {address} / it's ready for pickup at {pickup_point}.
> Nothing to pay — your price covered everything. Enjoy! 🇰🇷💙
> *(After delivery: “We'd love a photo + one line about your experience — may we share it?”)*

**RW**
> 🏠 *Biraje iwawe!*
> {name}, {item} yawe yarangije ibya gasutamo; {courier_name} arayikuzanira **{delivery_day}** kuri {address} / uyifatire kuri {pickup_point}.
> Nta mafaranga wishyura — byose byari mu giciro. Wishimire! 🇰🇷💙
> *(Nyuma yo kubona: “Twakwishimira ifoto n'ijambo rimwe ku byakugendekeye — twabisangiza abandi?”)*

---

## Supporting templates

### Quote — `/quote`

**EN**
> 💰 *Your CmartBridge quote*
> {item} — **{door_price} RWF, delivered to your door in Kigali.**
> ✔ Product + shipping + customs + VAT — everything included (breakdown available on request)
> ✔ Photo of your item before it ships
> ✔ Delivery 2–4 weeks · lost/damaged = reship or full refund
> To confirm: pay 100% to MTN MoMo **{momo_code}** (name: {account_name}) or Airtel Money **{airtel_code}** and send the screenshot. Quote valid {validity_days} days (exchange rates move!).

**RW**
> 💰 *Igiciro cyawe cya CmartBridge*
> {item} — **{door_price} RWF, kikugezweho i Kigali.**
> ✔ Igicuruzwa + ubwikorezi + imisoro — byose birimo (ibisobanuro ku gusaba)
> ✔ Ifoto y'igicuruzwa cyawe mbere yo koherezwa
> ✔ Bikugeraho mu byumweru 2–4 · bibuze/byangiritse = gusubizwa byose
> Kwemeza: yishyura byose kuri MTN MoMo **{momo_code}** ({account_name}) cyangwa Airtel Money **{airtel_code}** wohereze na screenshot. Igiciro kigumaho iminsi {validity_days}.

### Polite decline (prohibited/out-of-scope item) — `/decline`

**EN**
> 🙏 *Sorry — we can't bring this one.*
> {name}, we'd love to help, but **{item}** can't ship because: {reason — e.g. it contains a lithium battery, which airlines don't allow in post / it's over our 2 kg Phase 1 limit / it's restricted for import into Rwanda}.
> We've noted your request — if this becomes possible we'll message you first. Can we suggest an alternative? {alternative}

**RW**
> 🙏 *Tubabarire — iki ntidushobora kukizana.*
> {name}, twifuzaga kugufasha, ariko **{item}** ntigishobora koherezwa kubera: {reason}.
> Twanditse icyifuzo cyawe — nibishoboka tuzakumenyesha mbere ya bose. Twagusaba ikindi gisa na cyo? {alternative}

### Delay / customs hold — `/delay`

**EN**
> ⏳ *Small delay on your order — here's the honest update.*
> {item} is {reason — held at customs / delayed in transit}. New expected delivery: **{new_date}**.
> Your money and your item are safe, and our promise stands: if it can't be released, you get a full refund. We'll update you every {update_interval} days until it's resolved.

**RW**
> ⏳ *Hari gutinda gato — dore amakuru y'ukuri.*
> {item} {reason}. Itariki nshya iteganyijwe: **{new_date}**.
> Amafaranga yawe n'igicuruzwa cyawe biri amahoro; niba kidashoboye gusohoka, usubizwa amafaranga yose. Tuzakumenyesha buri minsi {update_interval} kugeza bikemutse.

---

**House style:** always the customer's name · always concrete dates · always “nothing more to pay” · answer within 24h · never promise faster than 2 weeks.
