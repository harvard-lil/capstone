<template>
  <main id="timeline-demo">
    <div class="row top-menu">
      <div class="header-section case-law-section">
        <span>CASE LAW</span>
        <button type="button" class="btn btn-tertiary" data-toggle="modal" data-target="#add-case-modal">
          <add-icon></add-icon>
        </button>
      </div>
      <div class="header-section other-events-section">
        <span>OTHER EVENTS</span>
        <button type="button" class="btn btn-tertiary" data-toggle="modal" data-target="#add-event-modal">
          <add-icon></add-icon>
        </button>
      </div>
      <div class="key-column">
        <button type="button" class="btn btn-tertiary">
          <key-icon @click="toggleKey"></key-icon>
        </button>
      </div>
    </div>
    <add-case-modal />
    <add-event-modal />
    <key v-show="keyShown"></key>

    <section id="timeline">
      <!-- YEAR -->
      <div class="year">
        <div class="incidental">
          <!-- CASE -->
          <article class="case">
            <header>
              Joe v. Volcano
            </header>
            <div class="links">
              <a href="details">details</a><br>
              <a href="#">read case</a></div>
          </article>
          <!-- /CASE -->
        </div>
        <div class="year_scale">
          1992
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e1992"></div>
          <div class="event_col ec_2 col-1 e1992"></div>
          <div class="event_col ec_3 col-1 e1992"></div>
          <div class="event_col ec_4 col-1 e1992"></div>
          <div class="event_col ec_5 col-1 e1992"></div>
          <div class="event_col ec_6 col-1 e1992"></div>
          <div class="event_col ec_7 col-1 e1992"></div>
          <div class="event_col ec_8 col-1 e1992"></div>
          <div class="event_col ec_9 col-1 e1992"></div>
          <div class="event_col ec_10 col-1 e1992"></div>
          <div class="event_col ec_11 col-1 e1992"></div>
          <div class="event_col ec_12 col-1 e1992"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">
          <!-- CASE -->
          <article class="case">
            <header>
              Joe v. Volcano
            </header>
            <div class="links">
              <a href="details">details</a><br>
              <a href="#">read case</a></div>
          </article>
          <!-- /CASE -->
        </div>
        <div class="year_scale">
          1993
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e1993"></div>
          <div class="event_col ec_2 col-1 e1993"></div>
          <div class="event_col ec_3 col-1 e1993"></div>
          <div class="event_col ec_4 col-1 e1993"></div>
          <div class="event_col ec_5 col-1 e1993"></div>
          <div class="event_col ec_6 col-1 e1993"></div>
          <div class="event_col ec_7 col-1 e1993"></div>
          <div class="event_col ec_8 col-1 e1993"></div>
          <div class="event_col ec_9 col-1 e1993"></div>
          <div class="event_col ec_10 col-1 e1993"></div>
          <div class="event_col ec_11 col-1 e1993"></div>
          <div class="event_col ec_12 col-1 e1993"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">

        </div>
        <div class="year_scale">
          1994
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e1994"></div>
          <div class="event_col ec_2 col-1 e1994"></div>
          <div class="event_col ec_3 col-1 e1994"></div>
          <div class="event_col ec_4 col-1 e1994"></div>
          <div class="event_col ec_5 col-1 e1994"></div>
          <div class="event_col ec_6 col-1 e1994"></div>
          <div class="event_col ec_7 col-1 e1994"></div>
          <div class="event_col ec_8 col-1 e1994"></div>
          <div class="event_col ec_9 col-1 e1994"></div>
          <div class="event_col ec_10 col-1 e1994"></div>
          <div class="event_col ec_11 col-1 e1994"></div>
          <div class="event_col ec_12 col-1 e1994"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">

        </div>
        <div class="year_scale">
          1995
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e1995"></div>
          <div class="event_col ec_2 col-1 e1995"></div>
          <div class="event_col ec_3 col-1 e1995"></div>
          <div class="event_col ec_4 col-1 e1995"></div>
          <div class="event_col ec_5 col-1 e1995"></div>
          <div class="event_col ec_6 col-1 e1995"></div>
          <div class="event_col ec_7 col-1 e1995"></div>
          <div class="event_col ec_8 col-1 e1995"></div>
          <div class="event_col ec_9 col-1 e1995"></div>
          <div class="event_col ec_10 col-1 e1995"></div>
          <div class="event_col ec_11 col-1 e1995"></div>
          <div class="event_col ec_12 col-1 e1995"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">
          <!-- CASE -->
          <article class="case">
            <header>
              Joe v. Volcano
            </header>
            <div class="links">
              <a href="details">details</a><br>
              <a href="#">read case</a></div>
          </article>
          <!-- /CASE -->
        </div>
        <div class="year_scale">
          1996
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e1996"></div>
          <div class="event_col ec_2 col-1 e1996"></div>
          <div class="event_col ec_3 col-1 e1996"></div>
          <div class="event_col ec_4 col-1 e1996"></div>
          <div class="event_col ec_5 col-1 e1996"></div>
          <div class="event_col ec_6 col-1 e1996"></div>
          <div class="event_col ec_7 col-1 e1996"></div>
          <div class="event_col ec_8 col-1 e1996"></div>
          <div class="event_col ec_9 col-1 e1996"></div>
          <div class="event_col ec_10 col-1 e1996"></div>
          <div class="event_col ec_11 col-1 e1996"></div>
          <div class="event_col ec_12 col-1 e1996"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">
          <!-- CASE -->
          <article class="case">
            <header>
              Joe v. Volcano part 2
            </header>
            <div class="links">
              <a href="details">details</a><br>
              <a href="#">read case</a></div>
          </article>
          <!-- /CASE -->
        </div>
        <div class="year_scale">
          1997
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e1997"></div>
          <div class="event_col ec_2 col-1 e1997"></div>
          <div class="event_col ec_3 col-1 e1997"></div>
          <div class="event_col ec_4 col-1 e1997"></div>
          <div class="event_col ec_5 col-1 e1997"></div>
          <div class="event_col ec_6 col-1 e1997"></div>
          <div class="event_col ec_7 col-1 e1997"></div>
          <div class="event_col ec_8 col-1 e1997"></div>
          <div class="event_col ec_9 col-1 e1997"></div>
          <div class="event_col ec_10 col-1 e1997"></div>
          <div class="event_col ec_11 col-1 e1997"></div>
          <div class="event_col ec_12 col-1 e1997"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">
          <!-- CASE -->
          <article class="case">
            <header>
              Joe v. Volcano
            </header>
            <div class="links">
              <a href="details">details</a><br>
              <a href="#">read case</a></div>
          </article>
          <!-- /CASE -->
        </div>
        <div class="year_scale">
          1998
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e1998"></div>
          <div class="event_col ec_2 col-1 e1998"></div>
          <div class="event_col ec_3 col-1 e1998"></div>
          <div class="event_col ec_4 col-1 e1998"></div>
          <div class="event_col ec_5 col-1 e1998"></div>
          <div class="event_col ec_6 col-1 e1998"></div>
          <div class="event_col ec_7 col-1 e1998"></div>
          <div class="event_col ec_8 col-1 e1998"></div>
          <div class="event_col ec_9 col-1 e1998"></div>
          <div class="event_col ec_10 col-1 e1998"></div>
          <div class="event_col ec_11 col-1 e1998"></div>
          <div class="event_col ec_12 col-1 e1998"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">

        </div>
        <div class="year_scale">
          1999
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e1999"></div>
          <div class="event_col ec_2 col-1 e1999"></div>
          <div class="event_col ec_3 col-1 e1999"></div>
          <div class="event_col ec_4 col-1 e1999"></div>
          <div class="event_col ec_5 col-1 e1999"></div>
          <div class="event_col ec_6 col-1 e1999"></div>
          <div class="event_col ec_7 col-1 e1999"></div>
          <div class="event_col ec_8 col-1 e1999"></div>
          <div class="event_col ec_9 col-1 e1999"></div>
          <div class="event_col ec_10 col-1 e1999"></div>
          <div class="event_col ec_11 col-1 e1999"></div>
          <div class="event_col ec_12 col-1 e1999"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">
          <!-- CASE -->
          <article class="case">
            <header>
              Joe v. Volcano 3
            </header>
            <div class="links">
              <a href="details">details</a><br>
              <a href="#">read case</a></div>
          </article>
          <!-- /CASE -->
          <!-- CASE -->
          <article class="case">
            <header>
              Joe v. Volcano 4
            </header>
            <div class="links">
              <a href="details">details</a><br>
              <a href="#">read case</a></div>
          </article>
          <!-- /CASE -->
        </div>
        <div class="year_scale">
          2000
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e2000"></div>
          <div class="event_col ec_2 col-1 e2000"></div>
          <div class="event_col ec_3 col-1 e2000"></div>
          <div class="event_col ec_4 col-1 e2000"></div>
          <div class="event_col ec_5 col-1 e2000"></div>
          <div class="event_col ec_6 col-1 e2000"></div>
          <div class="event_col ec_7 col-1 e2000"></div>
          <div class="event_col ec_8 col-1 e2000"></div>
          <div class="event_col ec_9 col-1 e2000"></div>
          <div class="event_col ec_10 col-1 e2000"></div>
          <div class="event_col ec_11 col-1 e2000"></div>
          <div class="event_col ec_12 col-1 e2000"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">
          <!-- CASE -->
          <article class="case">
            <header>
              Joe v. Volcano Returns
            </header>
            <nav>
              <a href="details">details</a><br>
              <a href="#">read case</a>
            </nav>
          </article>
          <!-- /CASE -->
          <!-- CASE -->
          <article class="case">
            <header>
              Joe v. Volcano: Joe Lives
            </header>
            <div class="links">
              <a href="details">details</a><br>
              <a href="#">read case</a>
            </div>
          </article>
          <!-- /CASE -->
        </div>
        <div class="year_scale">
          2001
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e2001"></div>
          <div class="event_col ec_2 col-1 e2001"></div>
          <div class="event_col ec_3 col-1 e2001"></div>
          <div class="event_col ec_4 col-1 e2001"></div>
          <div class="event_col ec_5 col-1 e2001"></div>
          <div class="event_col ec_6 col-1 e2001"></div>
          <div class="event_col ec_7 col-1 e2001"></div>
          <div class="event_col ec_8 col-1 e2001"></div>
          <div class="event_col ec_9 col-1 e2001"></div>
          <div class="event_col ec_10 col-1 e2001"></div>
          <div class="event_col ec_11 col-1 e2001"></div>
          <div class="event_col ec_12 col-1 e2001"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">

        </div>
        <div class="year_scale">
          2002
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e2002"></div>
          <div class="event_col ec_2 col-1 e2002"></div>
          <div class="event_col ec_3 col-1 e2002"></div>
          <div class="event_col ec_4 col-1 e2002"></div>
          <div class="event_col ec_5 col-1 e2002"></div>
          <div class="event_col ec_6 col-1 e2002"></div>
          <div class="event_col ec_7 col-1 e2002"></div>
          <div class="event_col ec_8 col-1 e2002"></div>
          <div class="event_col ec_9 col-1 e2002"></div>
          <div class="event_col ec_10 col-1 e2002"></div>
          <div class="event_col ec_11 col-1 e2002"></div>
          <div class="event_col ec_12 col-1 e2002"></div>
        </div>
      </div>
      <!-- /YEAR -->


      <!-- YEAR -->
      <div class="year">
        <div class="incidental">

        </div>
        <div class="year_scale">
          2003
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e2003"></div>
          <div class="event_col ec_2 col-1 e2003"></div>
          <div class="event_col ec_3 col-1 e2003"></div>
          <div class="event_col ec_4 col-1 e2003"></div>
          <div class="event_col ec_5 col-1 e2003"></div>
          <div class="event_col ec_6 col-1 e2003"></div>
          <div class="event_col ec_7 col-1 e2003"></div>
          <div class="event_col ec_8 col-1 e2003"></div>
          <div class="event_col ec_9 col-1 e2003"></div>
          <div class="event_col ec_10 col-1 e2003"></div>
          <div class="event_col ec_11 col-1 e2003"></div>
          <div class="event_col ec_12 col-1 e2003"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">

        </div>
        <div class="year_scale">
          2004
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e2004"></div>
          <div class="event_col ec_2 col-1 e2004"></div>
          <div class="event_col ec_3 col-1 e2004"></div>
          <div class="event_col ec_4 col-1 e2004"></div>
          <div class="event_col ec_5 col-1 e2004"></div>
          <div class="event_col ec_6 col-1 e2004"></div>
          <div class="event_col ec_7 col-1 e2004"></div>
          <div class="event_col ec_8 col-1 e2004"></div>
          <div class="event_col ec_9 col-1 e2004"></div>
          <div class="event_col ec_10 col-1 e2004"></div>
          <div class="event_col ec_11 col-1 e2004"></div>
          <div class="event_col ec_12 col-1 e2004"></div>
        </div>
      </div>
      <!-- /YEAR -->

      <!-- YEAR -->
      <div class="year">
        <div class="incidental">

        </div>
        <div class="year_scale">
          2005
        </div>
        <div class="spans row">
          <div class="event_col ec_1 col-1 e2005"></div>
          <div class="event_col ec_2 col-1 e2005"></div>
          <div class="event_col ec_3 col-1 e2005"></div>
          <div class="event_col ec_4 col-1 e2005"></div>
          <div class="event_col ec_5 col-1 e2005"></div>
          <div class="event_col ec_6 col-1 e2005"></div>
          <div class="event_col ec_7 col-1 e2005"></div>
          <div class="event_col ec_8 col-1 e2005"></div>
          <div class="event_col ec_9 col-1 e2005"></div>
          <div class="event_col ec_10 col-1 e2005"></div>
          <div class="event_col ec_11 col-1 e2005"></div>
          <div class="event_col ec_12 col-1 e2005"></div>
        </div>
      </div>
      <!-- /YEAR -->


    </section>
  </main>

</template>

<script>
import KeyIcon from '../../../../static/img/icons/key.svg';
import AddIcon from '../../../../static/img/icons/add.svg';
import Key from './key.vue';
import AddCaseModal from './add-case-modal.vue';
import AddEventModal from './add-event-modal.vue';

export default {
  name: 'Timeline',
  components: {
    KeyIcon,
    AddIcon,
    Key,
    AddCaseModal,
    AddEventModal,
  },

  data() {
    return {
      checked: false,
      title: 'Check me',
      addCaseModalShown: false,
      addEventModalShown: false,
      keyShown: false,

    }
  },
  methods: {
    check() {
      this.checked = !this.checked;
    },
    showAddEventModal() {
      this.addEventModalShown = true;
    },
    toggleKey() {
      this.keyShown = !this.keyShown;
    },
    // closeModal(e) {
    //   console.log("clicked", e)
    //   if (e.target !== $('div.modal-body')) {
    //     console.log("not modal-body")
    //   }
    // }
  }
};
</script>
